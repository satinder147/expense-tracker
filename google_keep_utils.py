import gkeepapi


class GoogleKeepUtils:

    def __init__(self, username, app_password):
        self.keeps_object = gkeepapi.Keep()
        self.keeps_object.login(username, app_password)

    def search_note_in_keeps(self, title):
        notes = self.keeps_object.find(func=lambda x: x.title == title)
        try:
            note = next(notes)
            return note
        except StopIteration:
            return None

    def add_transactions_to_google_keeps(self, note_title, transactions):
        already_existing_note = self.search_note_in_keeps(note_title)
        if already_existing_note:
            already_existing_note.delete()
        gnote = self.keeps_object.createNote(note_title, transactions)
        gnote.pinned = True
        self.keeps_object.sync()

    @staticmethod
    def prepare_message_for_google_keeps(data_df):
        text = """"""
        data_df['date'] = data_df['time'].apply(lambda x: str(x.date()))
        data_df['vendor'] = data_df['vendor'].apply(lambda x: x.lower())
        data_df['vendor_length'] = data_df['vendor'].apply(lambda x: len(x))
        for group_name, group in data_df.groupby('date'):
            text += '- ' + group_name + '\n'
            for idx, (_, row) in enumerate(group.iterrows()):
                text += "    {0} RS {2:^5},  {1:>5}({3})".format('*', row['vendor'], str(int(row['cost'])).rjust(5, ' '), row['card_no']) + '\n'
            text+='\n'
        total_per_card = data_df.groupby('card_no')['cost'].sum().to_dict()
        for card_no, total in total_per_card.items():
            text+= 'card - {},  total - {}\n'.format(str(card_no), str(total))
        text +='total {} \n'.format(data_df['cost'].sum())
        return text

    def register(self, data_df, current_month):
        transactions = self.prepare_message_for_google_keeps(data_df)
        self.add_transactions_to_google_keeps(current_month, transactions)