import re

class InteractionProfiling:

    def calculate_cumulative_score(self, new_email, keywords_scores, seen_keywords):
        """
        Calculates the cumulative normalized score for a conversation based on admin-defined thresholds.
        
        Args:
            new_email (str): The new email content to process.
            keywords_scores (dict): A dictionary of keywords with the required occurrence thresholds.
                                    Format: {keyword: required_frequency}.
            seen_keywords (dict): A dictionary tracking the frequency of seen keywords in the conversation.
                                Format: {keyword: seen_frequency}.
        
        Returns:
            tuple: Updated seen_keywords dictionary and the cumulative normalized score out of 100.
        """

        print('interaction_profiling function entered',keywords_scores, seen_keywords)
        # Tokenize and clean the email text
        words = re.findall(r'\b\w+\b', new_email.lower())

        # Update seen keywords with the new email
        for word in words:
            if word in keywords_scores:
                # Increment frequency but cap it at the admin-specified threshold
                seen_keywords[word] = min(seen_keywords.get(word, 0) + 1, keywords_scores[word])

        # Calculate the current score based on seen frequencies
        current_score = sum(seen_keywords[keyword]/keywords_scores[keyword] for keyword in seen_keywords)
        #current_score = sum(seen_keywords[keyword] for keyword in seen_keywords)

        # Calculate the maximum possible score
        max_score = len(keywords_scores)
        #max_score = sum(keywords_scores.values())

        # Normalize the score to 100
        normalized_score = (current_score / max_score) * 100 if max_score > 0 else 0
        print(normalized_score,seen_keywords)

        return seen_keywords, round(normalized_score, 2)


# interaction_profiling = InteractionProfiling()

# # Example Usage
# # Admin-defined keyword thresholds
# keywords_scores = {
#     "watches": 5,
#     "illicit": 5,
#     "trafficking": 3,
#     "stolen": 6,
#     "goods": 4,
#     "suspicious": 3
# }

# # Initialize seen keywords dictionary
# seen_keywords = {keyword: 0 for keyword in keywords_scores}

# # Simulate a conversation
# email_1 = "This conversation contains the keywords trafficking, stolen, illicit, and suspicious goods"
# email_2 = "This conversation contains the keywords trafficking, stolen, illicit, and suspicious goods"
# email_3 = "This conversation contains the keywords trafficking, stolen, illicit, and suspicious goods"
# email_4 = "This conversation contains the keywords trafficking, stolen, illicit, and suspicious goods"

# # Process emails
# seen_keywords, score_1 = interaction_profiling.calculate_cumulative_score(email_1, keywords_scores, seen_keywords)
# print(f"After email 1: Score = {score_1}, Seen Keywords = {seen_keywords}")

# seen_keywords, score_2 = interaction_profiling.calculate_cumulative_score(email_2, keywords_scores, seen_keywords)
# print(f"After email 2: Score = {score_2}, Seen Keywords = {seen_keywords}")

# seen_keywords, score_3 = interaction_profiling.calculate_cumulative_score(email_3, keywords_scores, seen_keywords)
# print(f"After email 3: Score = {score_3}, Seen Keywords = {seen_keywords}")

# seen_keywords, score_4 = interaction_profiling.calculate_cumulative_score(email_4, keywords_scores, seen_keywords)
# print(f"After email 3: Score = {score_4}, Seen Keywords = {seen_keywords}")
