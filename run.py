import logging
from pymongo import MongoClient
from estuda_transcript_api import EstudaTranscriptAPI

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(threadName)s %(asctime)s - %(levelname)s - %(message)s')

def connect_to_database():
    connection_string = "mongodb+srv://joaomello:sindria123@cluster0.z6hk7jp.mongodb.net/"
    client = MongoClient(connection_string)
    
    return client["ENEM_crawler"]

def main():
    logging.info('Starting the transcript process.')

    # Connect do Database
    db = connect_to_database()
    collection = db["estuda_lessons"]
    
    transcript_api = EstudaTranscriptAPI(collection)

    threads_count = 3
    transcript_api.execute_multithread(threads_count)

if __name__ == '__main__':
    main()
