import logging
from langchain_groq import ChatGroq

class ResponseGenerator:

    def __init__(self):
        # Initialize the LLM instance
        self.llm = ChatGroq(
            temperature=0.7,  # Adjusting temperature for more conversational responses
            groq_api_key="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",
            model_name="llama-3.1-8b-instant"
        )

    def generate_response(self, full_prompt):
        """
        Generates a response using an open-source LLM based on a prompt and email content.
        Args:
            prompt (str): The initial setup or scenario for the LLM to consider.
            email_content (str): The content of the incoming email to which we are responding.
            
        Returns:
            str: The generated response from the LLM.
        """
        #logging.info(full_prompt)
        
        response = self.llm.invoke(full_prompt)
        return response.content if response else "No response generated."

# # Test the function with a hardcoded prompt and email content
# prompt = "You are a police detective and posted an ad saying you are looking to buy watches at a cheap price in hope of catching some criminals. You received an email as below:"
# email_content = "Hi, I have a selection of premium watches available at very low prices. Let me know if you're interested."
# response_generator = ResponseGenerator()
# # Generate and log the response
# response = response_generator.generate_response(prompt, email_content)
# logging.info(f"In response generatore, generated: {response}")
