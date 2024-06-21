
from flask import Flask, render_template, request, send_file
import pandas as pd
import requests
import re
from transformers import PegasusForConditionalGeneration, PegasusTokenizer
from text_summary import summarizer
from datetime import datetime
import string
from collections import Counter
import matplotlib.pyplot as plt
import os

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('main.html')
    

@app.route('/extract')
def extract():
    return render_template('extract.html')

YOUTUBE_API_KEY = 'YOUR_API_KEY'

@app.route('/extract_comments', methods=['POST'])



def extract_comments():
    video_url = request.form['video_url']

    video_id_match = re.search(r'(?:https?:\/\/)?(?:www\.)?(?:youtube\.com\/(?:[^\/\n\s]+\/\S+\/|(?:v|e(?:mbed)?)\/|\S*?[?&]v=)|youtu\.be\/)([a-zA-Z0-9_-]{11})', video_url)
    if video_id_match:
        video_id = video_id_match.group(1)
    else:
        error_message = "Invalid YouTube video URL. Please enter a valid URL."
        return render_template('extract.html', error_message=error_message)

    
    comments, error_message = get_all_video_comments(video_id)

    
    if not comments and error_message:
        return render_template('extract.html', error_message=error_message)


    if not comments:
        no_comments_message = "No comments found for this video."
        return render_template('extract.html', no_comments_message=no_comments_message)

    save_to_excel(comments)

    return render_template('extract.html', comments_extracted=True)

def get_video_comments(video_id,page_token=None):
    url = f'https://www.googleapis.com/youtube/v3/commentThreads?part=snippet&videoId={video_id}&key={YOUTUBE_API_KEY}&maxResults=100'
    if page_token:
        url += f'&pageToken={page_token}'
    response = requests.get(url)
    return response.json()

def process_comments(comments_data):
    comments = []
    if 'items' in comments_data:
        for item in comments_data['items']:
            comment = {
                'date': item['snippet']['topLevelComment']['snippet']['publishedAt'],
                'comments': item['snippet']['topLevelComment']['snippet']['textDisplay']
            }
            comments.append(comment)
    return comments


def save_to_excel(comments):
    df = pd.DataFrame(comments)
    current_directory = os.path.dirname(os.path.realpath(__file__))
    file_path = os.path.join(current_directory, 'comments.xlsx')
    df.to_excel(file_path, index=False)

def get_all_video_comments(video_id):
    comments = []
    next_page_token = None

    while True:
        comments_data = get_video_comments(video_id, page_token=next_page_token)

        if 'error' in comments_data:
            error_message = comments_data['error']['message']
            return [], error_message

        current_comments = process_comments(comments_data)
        comments.extend(current_comments)

        if 'nextPageToken' in comments_data:
            next_page_token = comments_data['nextPageToken']
        else:
            break

    return comments, None

@app.route('/upload', methods=['POST'])
def upload_file():
    uploaded_file = request.files['file']
    if uploaded_file.filename != '':
        uploaded_file.save('comments.xlsx')
        return render_template('download.html')
    else:
        error_message = "No file uploaded. Please try again."
        return render_template('extract.html', error_message=error_message)
    
@app.route('/download')
def download_file():
    return send_file('comments.xlsx', as_attachment=True)



@app.route('/summarizer')
def summarizer_route():
    return render_template('summaryHome.html')   

@app.route('/extractiveSum')
def extractive_summery():
    return render_template('summary_input.html')


@app.route('/analyze', methods=['POST'])
def analyze():
    if request.method == 'POST':
        if 'google_sheet' not in request.files:
            return "No file part"

        google_sheet = request.files['google_sheet']
        
        if google_sheet.filename == '':
            return "No selected file"
        
        if google_sheet:
            
            df = pd.read_excel(google_sheet)  
          
            data = ' '.join(df['comments'])  
            summary, original_txt, len_orig_txt, len_summary = summarizer(data)

            return render_template('summary.html', summary=summary, original_txt=original_txt, len_orig_txt=len_orig_txt, len_summary=len_summary)






@app.route('/abstractiveSum')
def abstractive_summery():
    return render_template('summary_input2.html')   


# Load tokenizer and model
tokenizer = PegasusTokenizer.from_pretrained("google/pegasus-xsum")
model = PegasusForConditionalGeneration.from_pretrained("google/pegasus-xsum", from_tf=False)

# Ensure the "uploads" directory exists
uploads_dir = os.path.abspath("uploads")
if not os.path.exists(uploads_dir):
    os.makedirs(uploads_dir)

# Function to generate summary for a set of lines
def generate_summary_for_set(lines):
    combined_comments = ' '.join(lines)
    max_token_limit = model.config.max_position_embeddings
    max_length_percentage = 30
    max_length = min(max_token_limit, max(1, int(len(tokenizer.encode(combined_comments, return_tensors="pt")[0]) * (max_length_percentage / 100))))

    tokens = tokenizer(combined_comments, return_tensors="pt", max_length=max_length, truncation=True)
    summary_ids = model.generate(**tokens, max_length=max_length, length_penalty=2.0, num_beams=4, early_stopping=True)

    summary = tokenizer.decode(summary_ids[0], skip_special_tokens=True)

    return summary


@app.route('/uploadS', methods=['POST'])
def uploadS():
    print("Entering /upload route") 

    try:
        if 'file' not in request.files:
            return redirect_with_message('index', 'No file part')

        file = request.files['file']

        if file.filename == '':
            return redirect_with_message('index', 'No selected file')

        if file:
            
            file_path = os.path.join(uploads_dir, file.filename)
            file.save(file_path)

            
            df = pd.read_excel(file_path)
            comments = df['comments'].astype(str).tolist()

            
            if len(comments) <= 100:
                set_summary = generate_summary_for_set(comments)
                summaries = [set_summary]
            else:
                
                set_size = 100
                num_sets = len(comments) // set_size
                summaries = []

                for i in range(num_sets):
                    start_index = i * set_size
                    end_index = (i + 1) * set_size
                    set_summary = generate_summary_for_set(comments[start_index:end_index])
                    summaries.append(set_summary)

            
            print("Original Length:", len(comments))
            print("Summaries:", summaries)

            return render_template('ab_summary.html', original_length=len(comments), summaries=summaries)

    except PermissionError as e:
    
        print("PermissionError:", str(e))
        return redirect_with_message('index', 'Permission error')

    except Exception as e:
        
        print("Exception:", str(e))
        return render_template('error.html', error_message=str(e))

    return redirect_with_message('index', 'Unknown error')

def redirect_with_message(route, message):
    return redirect(url_for(route, message=message))



@app.route('/analyse')
def analyse():
    return render_template('analyseHome.html')


@app.route('/analyseBasedonTime')
def timeBasedAnalyse():
    return render_template('timeBasedAnalyse.html')

custom_sentiment_data = {}
with open('summarizer/sentimentDataSet.txt', 'r') as file:
    for line in file:
        word, sentiment = line.strip().split()
        custom_sentiment_data[word] = sentiment

def analyze_comments(comments, publish_date):
    results_by_time_frame = {}
    publish_date = datetime.strptime(publish_date, '%Y-%m-%d')

    for comment in comments:
        comment_date = datetime.strptime(comment['date'], '%Y-%m-%dT%H:%M:%SZ')
        time_frame = f"{comment_date.strftime('%Y-%m')}"

        if time_frame not in results_by_time_frame:
            results_by_time_frame[time_frame] = {'positive': 0, 'negative': 0, 'neutral': 0}

        for word in comment['text'].split():
            if word in custom_sentiment_data:
                sentiment = custom_sentiment_data[word]
                results_by_time_frame[time_frame][sentiment] += 1

    return results_by_time_frame


@app.route('/timeBasedupload', methods=['POST'])
def time_upload_file():
    uploaded_file = request.files['file']
    publish_date = request.form['publish_date']

    if uploaded_file.filename != '':
        file_path = 'summarizer/uploads/' + uploaded_file.filename
        uploaded_file.save(file_path)

        df = pd.read_excel(file_path)
        comments = [{'date': str(date), 'text': text} for date, text in zip(df['date'], df['comments'])]

        analysis_results = analyze_comments(comments, publish_date)

        return render_template('timeBasedresults.html', results=analysis_results)

    return "Error: No file uploaded."

@app.route('/analyseBasedonGraph')
def upload_sheet_for_graph_analyse():
    return render_template('upload.html')

def process_google_sheet(google_sheet):
    df = pd.read_excel(google_sheet) 
    comments_column = df['comments'].dropna() 

    
    return " ".join(comments_column)

@app.route('/analyzeforGraph', methods=['POST'])
def analyzeforGraph():
    if request.method == 'POST':
        if 'google_sheet' not in request.files:
            return "No file part"

        google_sheet = request.files['google_sheet']

        if google_sheet.filename == '':
            return "No selected file"

        if google_sheet:
            text = process_google_sheet(google_sheet)
            lower_case = text.lower()
            cleaned_text = lower_case.translate(str.maketrans('', '', string.punctuation))
            tokenized_words = cleaned_text.split()
            
            
            stop_words = ["i", "me", "my", "myself", "we", "our", "ours", "ourselves", "you", "your", "yours", "yourself",
                          "yourselves", "he", "him", "his", "himself", "she", "her", "hers", "herself", "it", "its", "itself",
                          "they", "them", "their", "theirs", "themselves", "what", "which", "who", "whom", "this", "that", "these",
                          "those", "am", "is", "are", "was", "were", "be", "been", "being", "have", "has", "had", "having", "do",
                          "does", "did", "doing", "a", "an", "the", "and", "but", "if", "or", "because", "as", "until", "while",
                          "of", "at", "by", "for", "with", "about", "against", "between", "into", "through", "during", "before",
                          "after", "above", "below", "to", "from", "up", "down", "in", "out", "on", "off", "over", "under", "again",
                          "further", "then", "once", "here", "there", "when", "where", "why", "how", "all", "any", "both", "each",
                          "few", "more", "most", "other", "some", "such", "no", "nor", "not", "only", "own", "same", "so", "than",
                          "too", "very", "s", "t", "can", "will", "just", "don", "should", "now"]

            final_words = []
            for word in tokenized_words:
                if word not in stop_words:
                    final_words.append(word)
            final_words = sorted(final_words)


            emotion_list = []
            with open('summarizer/emotion.txt', 'r') as file:
                for line in file:
                    clear_line = line.strip()
                    if ':' in clear_line:
                       word, emotion = clear_line.split(':')
                       if word in final_words:
                        emotion_list.append(emotion)



            sarcasm_list = []
            with open('summarizer/sarcasm_lexicon.txt', 'r') as file:
                sarcasm_lexicon = [line.strip() for line in file]

            for word in final_words:
                if word in sarcasm_lexicon:
                    sarcasm_list.append('sarcasm')


            slang_list = []
            with open('summarizer/slang_lexicon.txt', 'r') as file:
                slang_lexicon = [line.strip() for line in file]

            for word in final_words:
                if word in slang_lexicon:
                    slang_list.append('slang')
    

            w = Counter(emotion_list)
            sarcasm_counter = Counter(sarcasm_list)
            slang_counter = Counter(slang_list)


            combined_counter = w + sarcasm_counter + slang_counter


            fig, ax1 = plt.subplots()
            ax1.bar(combined_counter.keys(), combined_counter.values())
            fig.autofmt_xdate()
            graph_filename = os.path.join('sentiment_sarcasm_slang_graph.png')
            plt.savefig(graph_filename)
    
            plt.show()

        

            print("Emotion Counter:", w)
            print("Sarcasm Counter:", sarcasm_counter)
            print("Slang Counter:", slang_counter)
            print("Combined Counter:", combined_counter)
        
        

            return render_template('graphBasedresults.html', sentiment_sarcasm_slang_graph=graph_filename, emotion_counter=w, sarcasm_counter=sarcasm_counter, slang_counter=slang_counter, combined_counter=combined_counter)
            





if __name__ == "__main__":
    app.run(debug=True)
