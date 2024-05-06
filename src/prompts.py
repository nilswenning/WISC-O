prompts = {
    "german": {
        "call": {
            "short": {
                "system": """
        Du fasst Transkripte zusammen. Da Fehler beim Transkribieren passieren können,
        ist es wichtig, dass du eventuelle Logikfehler korrigierst.
        Stelle sicher, dass du ::title::, ::content::,
        ::list:: und ::stitle:: direkt in den Text einbindest.
        """,
                "user": """
        ::title::\n
        Fasse den Titel hier kurz zusammen und füge einen Zeilenumbruch ein.\n\n
        ::content::\n
        Fasse den Haupttext hier sehr ausführlich zusammen. Achte darauf, keine wichtigen Informationen wegzulassen.
        Formatiere den Text angemessen und füge danach einen Zeilenumbruch ein.\n\n
        ::list::\n
        Fasse den gesamten Text hier in einer Liste mit Stichpunkten zusammen. Schreibe dann in der nächsten Zeile.\n\n
        ::stitle::\n
        Fasse den gesamten Text hier in maximal zwei Wörtern zusammen.
        """
            }
        }
    },
    "english": {
        "call": {
            "short": {
                "system": """
        You will summarize transcripts. As transcription errors can occur,
        it's important that you correct any logical errors.
        Ensure to directly incorporate ::title::, ::content::,
        ::list::, and ::stitle:: into the text.
        """,
                "user": """
        ::title::\n
        Briefly summarize the title here and add a line break.\n\n
        ::content::\n
        Thoroughly summarize the main text here. Ensure no important information is omitted.
        Format the text appropriately and then add a line break.\n\n
        ::list::\n
        Summarize the entire text here in a bullet point list. Then, write on the next line.\n\n
        ::stitle::\n
        Summarize the entire text here in no more than two words.
        """
            }
        }
    }
}
