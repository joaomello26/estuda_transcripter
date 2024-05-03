import threading
import logging
import os
from transcription_utils import audio_downloader, transcript_audio

class EstudaTranscriptAPI:
    def __init__(self, collection):
        self.collection = collection

        # Create folder to save temporary audio files
        os.mkdir("audio_files")

    def __exit__(self):
        os.remove("audio_files")   

    def distribute_work(self, threads_count):
        collection = self.collection
        total_docs = collection.count_documents({})

        docs_per_thread = total_docs // threads_count
        remainder = total_docs % threads_count

        ranges = []
        start = 0

        for i in range(threads_count):
            # Parts with an index less than the remainder get an extra element
            end = start + docs_per_thread + (1 if i < remainder else 0) - 1
            ranges.append((start, end))
            start = end + 1

        return ranges

    def execute_multithread(self, threads_count):
        ranges = self.distribute_work(threads_count)
        threads = []

        for start, end in ranges:
            thread = threading.Thread(target=self.execute_batch, args=(start, end))

            threads.append(thread)
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()


    def execute_batch(self, start, end):
        collection = self.collection
        cursor = collection.find().skip(start).limit(end - start + 1)

        for document in cursor:
            if document['transcription'] != "":
                continue

            logging.info(f'Starting transcription of: {document['name']}')

            video_url = document['url']

            # Download audio file
            try:
                audio_filepath = audio_downloader(video_url)
            except Exception as e:
                logging.error(f"Error occurred: {e}")
                continue

            # Get audio transcription
            try:
                transcription = transcript_audio(audio_filepath)
            except Exception as e:
                logging.error(f"Error occurred: {e}")
                continue

            # Update in database
            self.collection.update_one(
                {"_id": document["_id"]},
                {"$set": {"transcription": transcription}}
            )

            # Delete file
            os.remove(audio_filepath)

            logging.info(f'Complete transcription of: {document['name']}')
