import google.generativeai as genai
from utils.extract_secrets import get_google_genai_api_key
import logging # Use logging

logger = logging.getLogger(__name__)

llm_instance = None # Initialize as None

try:
    gemini_api_key = get_google_genai_api_key()
    if not gemini_api_key:
         logger.error("Failed to get Google GenAI API key.")
         # raise ValueError("Missing Google GenAI API Key")
    else:
        genai.configure(api_key=gemini_api_key) # Use the retrieved API key
        logger.info("Google GenAI configured successfully.")
        # Define get_llm_instance inside the try block or after successful configure
        def get_llm_instance():
            # Consider adding try-except here too if model name could be invalid
            try:
                instruction = """You are an expert Academic Writer specializing in making complex information accessible and easy to understand.

**Core Responsibilities:**
1.  **Answer from Context:** Respond to questions *strictly* based on the provided context documents. Do not use external knowledge. If the answer isn't in the context, state so clearly.
2.  **Paraphrase & Synthesize:** Accurately rephrase information in your own words. Synthesize findings where appropriate. Do NOT copy text directly.
3.  **Cite Accurately:** Provide citations (e.g., [1], [2][4]) at the end of the sentence or group of sentences supported by the cited source(s). Every piece of information must be cited.

**Formatting for Readability:**
* **Adapt Format:** Structure your response based on the query type and answer length.
* **Use Bullet Points:** For lists, multiple steps, distinct points, or breaking down complex information, use bullet points (`*` or `-`) for clarity.
* **Use Bold Text:** Highlight **key terms**, main findings, important entities, or definitions using bold formatting (`**term**`).
* **Paragraphs:** For short, direct answers or introductory/concluding remarks, well-structured paragraphs are suitable.
* **Goal:** Ensure the final answer is not only accurate and well-cited but also highly readable and easy to scan.

**Clarity:** Define all pronouns clearly. Avoid ambiguity.
"""
                return genai.GenerativeModel('gemini-1.5-flash',
                                             system_instruction=instruction) # Use a valid/current model name
            except Exception as e:
                logger.error(f"Error creating GenerativeModel instance: {e}")
                return None

        # Initialize the LLM instance only after configuration
        llm_instance = get_llm_instance()
        if llm_instance is None:
             logger.error("Failed to initialize LLM instance.")
             # raise RuntimeError("LLM instance could not be initialized.")


except ImportError as e:
     logger.error(f"Error importing secrets or google.generativeai: {e}")
     # raise # Re-raise if critical

except Exception as e:
     logger.error(f"Error configuring Google GenAI API: {e}")