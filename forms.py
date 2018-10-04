from wtforms import Form, StringField, validators


class ClientForm(Form):
    apiKey = StringField('apiKey', [validators.Length(min=4, max=100)])
    secret = StringField('secret', [validators.Length(min=6, max=100)])

