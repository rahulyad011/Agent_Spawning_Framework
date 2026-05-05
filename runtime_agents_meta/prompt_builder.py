"""Dynamic prompt builder for meta-agent."""

from runtime_agents.shared.llm import LLMClient, Message
from runtime_agents.shared.logger import get_logger

logger = get_logger(__name__)


class DynamicPromptBuilder:
    """Builds system prompts dynamically based on requirements."""

    def __init__(self, llm: LLMClient):
        self.llm = llm

    async def build_prompt(self, requirement: str, context: str = "") -> str:
        """Build a dynamic system prompt for the requirement."""
        logger.debug("[PROMPT_BUILDER] Building dynamic prompt")

        prompt_prompt = f"""User requirement: {requirement}

{context}

Generate a system prompt that will guide an agent to complete this task effectively.
The prompt should:
1. Define the agent's role clearly
2. Specify how to approach the task
3. Include instructions for using available resources (files, databases, etc.)
4. Be specific and actionable

Return only the system prompt, no additional explanation."""

        try:
            generated_prompt = await self.llm.chat(
                [Message("user", prompt_prompt)], temperature=0.7
            )
            logger.debug(f"[PROMPT_BUILDER] Generated prompt length: {len(generated_prompt)}")
            return generated_prompt.strip()
        except Exception as e:
            logger.warning(f"[PROMPT_BUILDER] Error building prompt: {e}, using fallback")
            return f"You are a helpful assistant. Help the user with: {requirement}"
