from langchain_groq import ChatGroq

class ResponseGenerator:

    def __init__(self):
        # Initialize the LLM instance
        self.llm = ChatGroq(
            temperature=0.7,  # Adjusting temperature for more conversational responses
            groq_api_key="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",
            model_name="llama-3.1-8b-instant"
        )

    def generate_response(self, prompt, email_content):
        """
        Generates a response using an open-source LLM based on a prompt and email content.
        Args:
            prompt (str): The initial setup or scenario for the LLM to consider.
            email_content (str): The content of the incoming email to which we are responding.
            
        Returns:
            str: The generated response from the LLM.
        """
        print(prompt, email_content)
        full_prompt = (
            f"{prompt}\n\n"
            f"Received Email:\n'{email_content}'\n\n"
            "Reply in a way that seems human, showing interest in the offer but not too eager. "
            "Only reply the content of the reply and nothing else. Start the reponse with 'Hello', and then start the content of the email. End the email with Best, Jay. Make sure the response continues the facade that you are a buyer interested in the watches."
        )
        
        response = self.llm.invoke(full_prompt)
        return response.content if response else "No response generated."

# # Test the function with a hardcoded prompt and email content
# prompt = "You are a police detective and posted an ad saying you are looking to buy watches at a cheap price in hope of catching some criminals. You received an email as below:"
# email_content = "Hi, I have a selection of premium watches available at very low prices. Let me know if you're interested."
# response_generator = ResponseGenerator()
# # Generate and print the response
# response = response_generator.generate_response(prompt, email_content)
# print("In response generatore, generated: ", response)
