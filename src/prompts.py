prompts = {
    "german": {
        "call": {
            "system": """
                Du fasst Transkripte zusammen. Da Fehler beim Transkribieren passieren können,
                ist es wichtig, dass du eventuelle Logikfehler korrigierst.
                Formatiere den Text und schreibe den Output als Markdown-Text.
                """,
            "user": """
                Schreibe ein # gefolgt vom Wort 'Title:', und gib den Titel des Textes als Überschrift an.
                Füge dann einen Zeilenumbruch ein.\n\n
                Wenn ein Ereignis mit Datum erwähnt wird, schreibe dieses Ereignis mit Datum fett und kursiv am Anfang des Textes.
                Fasse den Haupttext kurz zusammen, ohne wichtige Informationen wegzulassen.
                Formatieren den Text angemessen und füge dann einen Zeilenumbruch hinzu.\n\n
                Erstelle eine ausführliche Zusammenfassung des gesamten Textes in Form einer Aufzählung.
            """
        },
        "YT-Summary": {
            "system": """
                Du fasst Transkripte zusammen. Da Fehler beim Transkribieren passieren können,
                ist es wichtig, dass du eventuelle Logikfehler korrigierst.
                Formatiere den Text. Schreibe den Output als Markdown-Text.
                """,
            "user": """
                Schreibe ein # gefolgt vom Wort 'Title:', und gib den Titel des Videos als Überschrift an.
                Füge dann einen Zeilenumbruch ein.\n\n
                Fasse alle im Video erwähnten Informationen in Stichpunkten zusammen, wobei keine Information fehlen sollte.
                Gehe auf jede Information in Unterstichpunkten sehr ausführlich ein.
                Wenn im Video eine Frage gestellt wird, beantworte diese mit Informationen aus dem Video.
                Formatieren den Text angemessen und füge dann einen Zeilenumbruch hinzu.\n\n
            """
        }
    },
    "english": {
        "call": {
            "system": """
                You summarize transcripts. Since transcription errors can occur, it's important that you correct any logical errors.
                Format the text. Write the output as Markdown text.
                """,
            "user": """
                Write a # followed by 'Title:', and then the title of the text as a heading.
                Add a line break.\n\n
                If an event with a date is mentioned, write this event with the date in bold and italic at the beginning of the text.
                Briefly summarize the main text ensuring no important information is missed.
                Format the text appropriately and then add a line break.\n\n
                Provide a detailed summary of the entire text in bullet points.
            """
        },
        "YT-Summary": {
            "system": """
                You summarize transcripts. Since transcription errors can occur, it's important that you correct any logical errors.
                Format the text. Write the output as Markdown text.
                """,
            "user": """
                Write a # followed by 'Title:', and then the title of the video as a heading.
                Add a line break.\n\n
                Summarize all mentioned information in the video using bullet points, ensuring that no information is missing.
                Address each piece of information in detailed sub-bullet points.
                If a question is asked in the video, answer it using the information from the video.
                Format the text appropriately and then add another line break.\n\n
            """
        }
    }
}
