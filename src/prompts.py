prompts = {
    "german": {
        "call": {
            "system": """
                Du fasst Transkripte ausführlich zusammen. Da Fehler beim Transkribieren passieren können,
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
                Du fasst ausführlich Transkripte zusammen. Da Fehler beim Transkribieren passieren können, ist es wichtig, dass du eventuelle Logikfehler korrigierst.
                Formatiere den Text. Schreibe den Output als Markdown-Text.
                """,
            "user": """
                Schreibe ein # gefolgt vom Wort 'Title:', und gib den Titel des Videos als Überschrift an.
                Füge dann einen Zeilenumbruch ein.\n\n
                Fasse alle erwähnten Informationen ausführlich in Stichpunkten zusammen, einschließlich detaillierter Beispiele und direkter Zitate aus dem Video. Erkläre jede wichtige Aussage und ihre Bedeutung.
                Gehe in Unterpunkten weiter auf die jeweiligen Informationen und Themen des Videos ein. Gib den Sachverhalt ausführlich in diesen Unterpunkten wieder und erkläre die Implikationen.
                Wenn im Video eine Frage gestellt wird, entwickle eine gut begründete Antwort basierend auf den Informationen aus dem Video.
                Reflektiere über mögliche Implikationen oder Lehren aus dem Videoinhalt.
                Formatieren den Text angemessen und füge dann zwei Zeilenumbrüche hinzu.\n\n
            """
        }
    },
    "english": {
        "call": {
            "system": """
                You summarize transcripts in detail. Since transcription errors can occur, it's important that you correct any logical errors.
                Format the text and write the output as Markdown text.
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
                You summarize transcripts in detail. Since transcription errors can occur, it's important that you correct any logical errors.
                Format the text. Write the output as Markdown text.
                """,
            "user": """
                Write a # followed by 'Title:', and then the title of the video as a heading.
                Add a line break.\n\n
                Summarize all mentioned information in the video in detail using bullet points, including detailed examples and direct quotes from the video. Explain each significant statement and its implications.
                Delve into the respective information and themes of the video in sub-points. Elaborately recount the subject matter in these sub-points and explain the implications.
                If a question is asked in the video, develop a well-reasoned answer using the information from the video.
                Reflect on possible implications or lessons from the video content.
                Format the text appropriately and then add two line breaks.\n\n
            """
        }
    }
}
