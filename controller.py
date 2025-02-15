import os
import csv
from io import StringIO
import streamlit as st
 # Add Azure OpenAI package
from openai import AzureOpenAI
from dotenv import load_dotenv
from collections import Counter


# Load environment variables from the .env file
load_dotenv()

client = AzureOpenAI(
    azure_endpoint=os.getenv("OPENAI_API_BASE"),  # Ensure this environment variable is set correctly
    api_key=os.getenv("OPENAI_API_KEY"),
    api_version="2024-08-01-preview"  # Use the appropriate API version
)

    
# Create a system message
system_message = """"You are an AI education specialist tasked with creating a comprehensive AI Competency Framework that includes key areas such as AI Literacy, Data Reasoning, and Ethical Awareness. Based on this framework, design an assessment consisting of 50-100 questions. Ensure a balanced mix of multiple-choice questions (MCQs). Each question should be clear, concise, and aligned with the competencies outlined in the framework."

Guidelines for Developing the Framework and Questions:

AI Literacy:

Definition: Understanding fundamental AI concepts, technologies, and their applications.
Sample MCQ: "Which of the following best describes machine learning? "
Data Reasoning:

Definition: Ability to interpret, analyze, and make decisions based on data.
Sample MCQ: "What is the primary purpose of data normalization in machine learning?"

Ethical Awareness:

Definition: Recognizing and addressing moral implications and biases in AI systems.
Sample MCQ: "Which ethical concern arises when AI systems make decisions based on biased data?"

Do not generate options for the questions
"""


def generate_questions(topic_prompt, system_message, num_questions):
    response = client.chat.completions.create(
        model=os.getenv("OPENAI_API_BASE"),
        temperature=0.7,
        n=num_questions,
        messages=[
            {"role": "system", "content": system_message},
            {"role": "user", "content": f" Generate questions based on the topic prompt: {topic_prompt} and number of questions:  {num_questions}"}
        ]
    )
    print("Questions have been generated successfully.") 
    print(response.choices[0].message.content)
    return response.choices[0].message.content

def validate_questions_batch(questions, model_deployment):
    system_message = """
    You are a question validator that evaluates questions for clarity and relevance. For each question, respond with 'yes' if it's appropriate or 'no' if it's not. 
    For example: "What is the primary purpose of data normalization in machine learning? : yes
    """
    prompt = f"Evaluate the following questions for clarity and relevance:\n\n" + "\n".join(questions) + "\n\nFor each question, respond with 'yes' if it's appropriate or 'no' if it's not."
    response = client.chat.completions.create(
        model=model_deployment,
        temperature=0.7,
        messages=[
            {"role": "system", "content": system_message},
            {"role": "user", "content": prompt}
        ]
    )
    evaluations = response.choices[0].message.content.strip().split('\n')
    #print(f"Validation results from {model_deployment}: {evaluations}")
    return evaluations

def generate_answer(question):
    system_message = """
    You are an answer generator that provides concise answers to questions based on the validated questions.
    Always give your answer to each question liek this:
    "Question: Which of the following best describes machine learning? 
    Answer: Machine learning is a subset of artificial intelligence (AI) that focuses on the development of algorithms and models that allow computers to learn and make decisions based on data."
    """
    prompt = f"Provide a concise answer to the following question:\n\n{question}"
    response = client.chat.completions.create(
        model="gpt-4",
        temperature=0.7,
        messages=[
            {"role": "system", "content": system_message},
            {"role": "user", "content": prompt}
        ]
    )
    print("Answer has been generated successfully.")
    return response.choices[0].message.content.strip()

def generate_options_and_answer(question):
    # OpenAI function call to generate options for the question
    options = []
    answer = ""
    
    # Define OpenAI API call to generate options for the question
    response = client.chat.completions.create(
        model="gpt-4",  # Use appropriate model
         messages=[
            {"role": "system", "content": f"Generate multiple choice options for the following question, make sure the options are related to the question and do not repeat the options. Always add the answer to the last option."},
            {"role": "user", "content": f"Question: {question}"},
        ],
        temperature=0.7
    )
    # Split the response into options (assuming each option is on a new line)
    options = response.choices[0].message.content
    
    # Get the correct answer (we assume the last option is the correct one)
    answer = options[-1]
    
    return options, answer

def save_questions_to_csv(question_data):
    # Convert question_data to a CSV string and return as a file-like object
    if not question_data:
        return None  # Return None if no question data

    output = StringIO()
    writer = csv.DictWriter(output, fieldnames=["question", "options", "answer"])
    writer.writeheader()
    for data in question_data:
        writer.writerow(data)
    
    # Move the cursor to the beginning of the StringIO object for reading
    output.seek(0)
    return output.getvalue()  # Return CSV as a string for downloading
            
def gen( topic_prompt, system_message, num_questions):

    questions = generate_questions(topic_prompt, system_message, num_questions)

    # Step 2: Validate questions using three different models
    validation_models = [
        "gpt-4o",  # Replace with your actual validator model deployment names
        "gpt-4o",
        "gpt-4o"
    ]

    # Collect evaluations from all validators
    all_evaluations = []
    for model in validation_models:
        evaluations = validate_questions_batch(questions, model)
        all_evaluations.append(evaluations)
        print(all_evaluations)
        # Step 1: Flatten the list
        flattened_list = [item for sublist in all_evaluations for item in sublist]

        # Step 2: Convert all elements to strings (if they're not already)
        flattened_list = list(map(str, flattened_list))

        # Step 3: Join the elements into a single string with newline separators
        formatted_prompt = "\n".join(flattened_list)

        # Print or use the formatted prompt
        print(formatted_prompt)

    print("Validated question-answer pairs have been saved to 'validated_qas.txt'.")

# Step 2: Split the combined text into individual question-answer pairs
# Assuming each pair ends with "']" and is separated by ", '"
    pairs = formatted_prompt.split("\n")  # Assuming this is already created from your earlier code
    
    question_yes_count = {}
    
    # Process each pair and count "yes" answers
    for pair in pairs:
        if " : " in pair:
            question_part, answer_part = pair.split(" : ", 1)
            question = question_part.strip()
            answer = answer_part.strip().lower()  # Normalize the answer to lowercase

            # Count the occurrences of "yes" for each question
            if answer == "yes":
                if question in question_yes_count:
                    question_yes_count[question] += 1
                else:
                    question_yes_count[question] = 1
    
    # Collect questions with more than two "yes" answers
    questions_list = []
    print("Questions with more than two 'yes' answers:")
    for question, count in question_yes_count.items():
        if count > 2:
            print(f"Question: {question}")
            print(f"Number of 'yes' answers: {count}")
            print("-" * 50)
            questions_list.append(question)
    print(questions_list)
    # Step to generate options and answers for the filtered questions
    question_data = []
    for question in questions_list:
        options, answer = generate_options_and_answer(question)
        question_data.append({
            "question": question,
            "options": options,
            "answer": answer
        })

    return question_data
    # save_questions_to_csv(question_data)
    # import pandas as pd
    # read_file = pd.read_csv (r'questions_and_answers.csv')
    # print (read_file)
    # print("Questions with options and answers have been saved to 'questions_and_answers.csv'.")
def main():
    st.title("AI Competency Framework Question Generator")
    topic_prompt = st.text_input("Enter the topic prompt:", "AI")
    num_questions = st.number_input("Number of questions to generate:", min_value=1, max_value=100, value=5)

    if st.button("Generate Questions"):
        with st.spinner("Generating questions..."):
            question_data = gen(topic_prompt, system_message, num_questions)
            print(f"question_data: {question_data}")
            #save_questions_to_csv(question_data)
            if question_data:
                csv = save_questions_to_csv(question_data)
                st.download_button(
                    label="Download CSV",
                    data= csv ,
                    file_name="questions_and_answers.csv",
                    mime="text/csv"
                )
            else:
                st.warning("No questions generated.")

# Run the app
if __name__ == "__main__":
    main()


