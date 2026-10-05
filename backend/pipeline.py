"""
Orchestration graph — mirrors the visual builder flow exactly:

  Knowledge Retrieval
        |
  Classifier / Router
        |
  Condition / Branch  --check the user access-->  Authorized / Unauthorized
        |authorized                                   |unauthorized
        v                                              v
     LLM Step                                    Human Handoff
   (generate cited answer)                     (escalate to admin)
        |
   Custom Code (format response)
        |
   Evaluator / Guardrail (validate response)
        |
   Condition / Branch --did it pass validation?--> pass / fail
        |pass                                         |fail
        v                                              v
   Output Formatter                          Retry / Fallback
   (format final answer)                    (retry, up to MAX_RETRIES)
                                             fail path loops back to LLM Step

Every node execution is appended to a `trace` list so the frontend can
render the same step-by-step path shown in the visual builder.
"""
import datetime
import config
import retrieval
import access_control
import llm_client
import guardrail

SYSTEM_PROMPT = (
    "You are a secure enterprise knowledge assistant. Generate a response "
    "using ONLY the retrieved enterprise knowledge provided in CONTEXT. "
    "Do not use outside knowledge. Every factual claim must include a "
    "citation to its source using the format [n] referencing the numbered "
    "context passages. If the context does not answer the question, say so."
)


def _node(trace, node_type, label, detail, extra=None):
    trace.append({
        "node_type": node_type,
        "label": label,
        "detail": detail,
        "timestamp": datetime.datetime.utcnow().isoformat(timespec="seconds") + "Z",
        **({"extra": extra} if extra else {}),
    })


def run_pipeline(user_id: str, query: str) -> dict:
    trace = []

    # ---- 1. Knowledge Retrieval ----
    retrieved = retrieval.retrieve(query)
    _node(trace, "knowledge_retrieval", "Knowledge Retrieval",
          f"Retrieved {len(retrieved)} relevant enterprise document(s).",
          extra=[{"title": d["title"], "id": d["id"], "score": round(d["score"], 3)} for d in retrieved])

    # ---- 2. Classifier / Router ----
    departments = access_control.classify(retrieved)
    _node(trace, "classifier_router", "Classifier / Router",
          f"Classified request under department(s): {', '.join(departments)}.")

    # ---- 3. Condition / Branch: check the user access ----
    branch, allowed_docs, denied_docs, user = access_control.check_access(user_id, retrieved)
    _node(trace, "condition_branch", "Condition / Branch",
          f"Checked user access for '{user['name']}' (role: {user['role']}) -> {branch}.",
          extra={"branch": branch, "denied_titles": [d["title"] for d in denied_docs]})

    if branch == "not_found":
        # ---- No matching knowledge at all: NOT an access issue, so no handoff ----
        _node(trace, "knowledge_gap", "Knowledge Gap",
              "No enterprise document matched this question closely enough to answer it.")
        return {
            "answer": (
                "I couldn't find anything in the enterprise knowledge base that answers that. "
                "Try asking about HR, Finance, Legal, or Engineering topics, or upload a relevant "
                "document so it can be indexed."
            ),
            "citations": [],
            "status": "not_found",
            "trace": trace,
        }

    if branch == "unauthorized":
        # ---- Human Handoff ----
        _node(trace, "human_handoff", "Human Handoff",
              "User lacks permission for the retrieved knowledge. Escalated to admin for review.")
        return {
            "answer": (
                "I found documents that may be relevant, but you don't currently have access to them "
                "based on your role. This request has been escalated to an administrator for review."
            ),
            "citations": [],
            "status": "escalated",
            "trace": trace,
        }

    # ---- 4/5/6. LLM Step -> Custom Code -> Evaluator/Guardrail, with retry loop ----
    answer, formatted_citations = "", []
    attempt = 0
    while True:
        attempt += 1
        context_block = "\n".join(
            f"[{i+1}] ({d['title']}) {d['text']}" for i, d in enumerate(allowed_docs)
        )
        user_prompt = f"CONTEXT:\n{context_block}\n\nQUESTION:\n{query}"

        # ---- LLM Step ----
        raw_answer = llm_client.chat_completion(SYSTEM_PROMPT, user_prompt)
        _node(trace, "llm_step", "LLM Step",
              f"Generated a secure, cited response based only on retrieved enterprise knowledge (attempt {attempt}).")

        # ---- Custom Code: format response ----
        formatted_citations = [{"n": i + 1, "title": d["title"], "id": d["id"]} for i, d in enumerate(allowed_docs)]
        answer = raw_answer
        _node(trace, "custom_code", "Custom Code",
              "Formatted response: normalized citation markers and attached source metadata.")

        # ---- Evaluator / Guardrail: validate response ----
        result = guardrail.validate(answer, allowed_docs)
        _node(trace, "evaluator_guardrail", "Evaluator / Guardrail",
              "Checked output against policy, quality bar, and citation requirements.",
              extra=result)

        # ---- Condition / Branch: did the response pass validation ----
        verdict = "pass" if result["passed"] else "fail"
        _node(trace, "condition_branch", "Condition / Branch",
              f"Did the response pass validation? -> {verdict}.")

        if verdict == "pass":
            break

        if attempt > config.MAX_RETRIES:
            # ---- Retry / Fallback exhausted -> safe fallback answer ----
            _node(trace, "retry_fallback", "Retry / Fallback",
                  f"Max retries ({config.MAX_RETRIES}) exhausted. Returning safe fallback response.")
            answer = (
                "I wasn't able to produce a fully policy-compliant, cited answer from the "
                "available enterprise knowledge. Please rephrase your question or contact "
                "the relevant department directly."
            )
            formatted_citations = []
            break

        # ---- Retry / Fallback: retry on failure ----
        _node(trace, "retry_fallback", "Retry / Fallback",
              f"Validation failed ({'; '.join(result['reasons'])}). Retrying LLM Step (attempt {attempt + 1}).")

    # ---- Output Formatter: format final answer ----
    _node(trace, "output_formatter", "Output Formatter", "Formatted final answer for delivery to the UI.")

    return {
        "answer": answer,
        "citations": formatted_citations,
        "status": "answered",
        "trace": trace,
    }
