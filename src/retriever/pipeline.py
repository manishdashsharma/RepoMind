from __future__ import annotations

from collections.abc import Generator
from dataclasses import dataclass

from zeocloud.embedder.embed import EmbedClient
from zeocloud.llm.ollama import LLMClient
from zeocloud.retriever.qdrant import SearchResult, VectorStore


@dataclass
class ConversationTurn:
    question: str
    answer: str
    project: str
    sources: list[str]


def _system_prompt(agent_name: str, project: str) -> str:
    return (
        f"You are {agent_name}, the AI assistant built into Zeocloud"
        " — a developer tool that helps engineers understand codebases"
        " without sending a single byte to the cloud.\n\n"
        f'You are currently helping with the project: "{project}"\n\n'
        "CRITICAL LANGUAGE RULE:\n"
        "- Detect the language/style of the user's question and match it exactly\n"
        "- Hinglish (Hindi + English mix) → reply in Hinglish — this is natural for Indian devs\n"
        "- Pure Hindi → reply in Hindi\n"
        "- Pure English → reply in English\n"
        "- NEVER give the same answer in two languages. Pick one style and stick to it.\n\n"
        "Your identity:\n"
        "- You have read and understood the code in this project deeply\n"
        "- Answer ONLY from the code context below — if not in context, say so\n"
        "- Do not use general framework knowledge to fill gaps — stick to what the code shows\n"
        "- You are concise, direct, and developer-first — no fluff\n"
        "- If you spot a bug or security issue in the shown code, mention it\n\n"
        "Format guidelines:\n"
        "- Use code blocks with language tags for all code\n"
        "- Cite file paths and line numbers when referencing code\n"
        "- For longer answers, use bullet points or numbered steps\n\n"
        "You run locally on the developer's machine."
        " No data leaves their computer. This is the Zeocloud promise."
    )


class RAGPipeline:
    def __init__(
        self,
        llm: LLMClient,
        embedder: EmbedClient,
        store: VectorStore,
        model: str,
        agent_name: str = "Zeocloud",
    ) -> None:
        self._llm = llm
        self._embedder = embedder
        self._store = store
        self._model = model
        self._agent_name = agent_name
        self._history: list[ConversationTurn] = []

    def ask(
        self,
        project: str,
        question: str,
        top_k: int = 8,
    ) -> Generator[str, None, None]:
        query_vector = self._embedder.embed(question)
        results = self._store.search(project, query_vector, top_k=top_k)

        if not results:
            answer = (
                f"I couldn't find relevant code in **{project}** for that question.\n\n"
                "Suggestions:\n"
                "- Try different keywords or a more specific question\n"
                "- Make sure the project was indexed recently\n"
                "- Use `zeocloud reindex <project>` if you've added new files"
            )
            yield answer
            self._history.append(ConversationTurn(question, answer, project, []))
            return

        system = _system_prompt(self._agent_name, project)
        prompt = self._build_prompt(question, results)

        collected: list[str] = []
        for token in self._llm.generate_stream(self._model, prompt, system=system):
            collected.append(token)
            yield token

        sources = list(dict.fromkeys(r.file_path for r in results))
        answer_text = "".join(collected)
        self._history.append(ConversationTurn(question, answer_text, project, sources))

        yield "\n\n---\n**Sources:**\n"
        for src in sources:
            matching = next((r for r in results if r.file_path == src), None)
            if matching:
                yield f"- `{src}` · lines {matching.start_line}–{matching.end_line}\n"

    def clear_history(self) -> None:
        self._history.clear()

    @property
    def history(self) -> list[ConversationTurn]:
        return list(self._history)

    def _build_prompt(self, question: str, results: list[SearchResult]) -> str:
        context_parts: list[str] = []
        for i, r in enumerate(results, start=1):
            context_parts.append(
                f"[{i}] {r.file_path} (lines {r.start_line}–{r.end_line}, {r.language})\n"
                f"```{r.language}\n{r.content.rstrip()}\n```"
            )

        history_context = ""
        if self._history:
            recent = self._history[-3:]
            turns = []
            for turn in recent:
                turns.append(f"Q: {turn.question}\nA: {turn.answer[:500]}...")
            history_context = "\n\nRecent conversation:\n" + "\n\n".join(turns) + "\n"

        return (
            f"Code context from the project:{history_context}\n\n"
            + "\n\n".join(context_parts)
            + f"\n\n---\n\nCurrent question: {question}\n\nAnswer:"
        )
