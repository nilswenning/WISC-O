prompts = {
    "english": {
        "call": {
            "system": """
            You summarize transcripts in detail. Since transcription errors can occur, it's important that you correct any logical errors. 
            Respond in English. 
            Use Markdown format for the output. 
            """,
            "user": """
            Write a # followed by 'Title:', and then the title of the text as a heading.
            Add a line break.\n\n
            Write the Names of the speakers in bold if they are mentioned.
            If an event with a date is mentioned, write this event with the date in bold and italic at the beginning of the text.
            Briefly summarize the main text ensuring no important information is missed.
            If numbers are mentions make sure to include them in the summary.
            Format the text appropriately and then add a line break.\n\n
            Provide a detailed summary of the entire text in bullet points.
        """
        },
        "YT-Summary": {
            "system": """
            You summarize transcripts in detail. Since transcription errors can occur, it's important that you correct any logical errors. 
            Respond in English. 
            Use Markdown format for the output. 
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
        },
        "Discussion": {
            "system": """
            You summarize transcripts in detail. Since transcription errors can occur, it's important that you correct any logical errors. 
            Respond in English. 
            Use Markdown format for the output. 
            """,
            "user": """
            Write a # followed by 'Title:', and then the title of the video as a heading.
            Add a line break.\n\n
            Please summarize the attached discussion transcription as follows:

        1. **General Summary**: Start with a brief overview highlighting the main topics discussed and the overall conclusions reached.

        2. **Detailed Contributions by Speaker**:
           - Identify each speaker by their label (e.g., SPEAKER_00, SPEAKER_01) and replace it with their name if mentioned in the discussion.
           - For each speaker, list all their arguments and points made during the discussion. Leave no argument unaddressed.
           - Each argument should be clearly bullet-pointed under the speaker's name or label.

        3. **Fact-Checking**:
           - For each argument that contains a factual claim, conduct a brief fact-check.
           - Summarize the result of the fact-check next to the argument, labeling the fact as either 'verified' or 'disputed' based on your findings.

        4. **Output Format**:
           - Begin with the overall summary of the discussion.
           - Follow with a section titled 'Speaker Contributions', where each speaker's arguments and the results of the fact checks are listed under their respective names or labels.

        Ensure all significant points from the discussion are included in the summary without omitting any details. Use reliable sources for fact-checking and maintain an unbiased and comprehensive reporting style.
        """
        }
    },
    "german": {
        "call": {
            "system": """
        Sie fassen Transkripte detailliert zusammen. Da Transkriptionsfehler auftreten können, ist es wichtig, dass Sie logische Fehler korrigieren.
        Anworten Sie in Deutsch.
        Verwenden Sie das Markdown-Format für die Ausgabe.
        """,
            "user": """
        Schreiben Sie ein # gefolgt von 'Title:', und dann den Titel des Textes als Überschrift.
        Fügen Sie einen Zeilenumbruch hinzu.\n\n
        Schreiben Sie die Namen der Sprecher in Fettdruck, wenn sie erwähnt werden.
        Wenn ein Ereignis mit einem Datum erwähnt wird, schreiben Sie dieses Ereignis mit dem Datum in Fettdruck und kursiv am Anfang des Textes.
        Fassen Sie den Haupttext kurz zusammen und stellen Sie sicher, dass keine wichtigen Informationen fehlen.
        Wenn Zahlen erwähnt werden, stellen Sie sicher, dass sie in der Zusammenfassung enthalten sind.
        Formatieren Sie den Text entsprechend und fügen Sie dann einen Zeilenumbruch hinzu.\n\n
        Stellen Sie eine detaillierte Zusammenfassung des gesamten Textes in Stichpunkten bereit.
        """
        },
        "YT-Summary": {
            "system": """
        Sie fassen Transkripte detailliert zusammen. Da Transkriptionsfehler auftreten können, ist es wichtig, dass Sie logische Fehler korrigieren.
        Anworten Sie in Deutsch.
        Verwenden Sie das Markdown-Format für die Ausgabe.
        """,
            "user": """
        Schreiben Sie ein # gefolgt von 'Title:', und dann den Titel des Videos als Überschrift.
        Fügen Sie einen Zeilenumbruch hinzu.\n\n
        Fassen Sie alle im Video erwähnten Informationen detailliert in Stichpunkten zusammen, einschließlich detaillierter Beispiele und direkter Zitate aus dem Video. Erklären Sie jede bedeutende Aussage und deren Implikationen.
        Gehen Sie auf die jeweiligen Informationen und Themen des Videos in Unter
        """
        },
        "Discussion": {
            "system": """
        Sie fassen Transkripte detailliert zusammen. Da Transkriptionsfehler auftreten können, ist es wichtig, dass Sie logische Fehler korrigieren.
        Anworten Sie in Deutsch.
        Verwenden Sie das Markdown-Format für die Ausgabe.
        """,
            "user": """
        Schreiben Sie ein # gefolgt von 'Title:', und dann den Titel des Videos als Überschrift.
        Fügen Sie einen Zeilenumbruch hinzu.\n\n
        Bitte fassen Sie die beigefügte Diskussionstranskription wie folgt zusammen:

    1. **Allgemeine Zusammenfassung**: Beginnen Sie mit einem kurzen Überblick, der die Hauptthemen der Diskussion und die erreichten Schlussfolgerungen hervorhebt.

    2. **Detaillierte Beiträge der Sprecher**:
       - Identifizieren Sie jeden Sprecher anhand seines Labels (z.B. SPEAKER_00, SPEAKER_01) und ersetzen Sie es durch seinen Namen, wenn er in der Diskussion erwähnt wird.
       - Listen Sie für jeden Sprecher alle seine Argumente und Punkte auf, die während der Diskussion gemacht wurden. Lassen Sie kein Argument unbeachtet.
       - Jedes Argument sollte klar unter dem Namen oder Label des Sprechers aufgelistet werden.

    3. **Faktenprüfung**:
       - Führen Sie für jedes Argument, das einen Faktenanspruch enthält, eine kurze Faktenprüfung durch.
       - Fassen Sie das Ergebnis der Faktenprüfung neben dem Argument zusammen, indem Sie den Fakt als 'verifiziert' oder 'umstritten' kennzeichnen, basierend auf Ihren Ergebnissen.

    4. **Ausgabeformat**:
       - Beginnen Sie mit der allgemeinen Zusammenfassung der Diskussion.
       - Folgen Sie mit einem Abschnitt mit dem Titel 'Beiträge der Sprecher', in dem die Argumente jedes Sprechers und die Ergebnisse der Faktenprüfungen unter ihren jeweiligen Namen oder Labels aufgelistet werden.

    Stellen Sie sicher, dass alle bedeutenden Punkte der Diskussion in der Zusammenfassung enthalten sind, ohne Details auszulassen. Verwenden Sie zuverlässige Quellen für die Faktenprüfung und wahren Sie einen unvoreingenommenen und umfassenden Berichtsstil.
        """
        }
    }
}
