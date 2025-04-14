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
                instruction = "You are an expert Academic Writer, specializes in translating technical or scientific information into accessible language for broader audiences,\
            focuses on summarizing, analyzing, and responding to academic literature effectively."
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