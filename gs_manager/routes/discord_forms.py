from flask_wtf import FlaskForm
from wtforms import StringField, IntegerField, BooleanField, SelectMultipleField
from wtforms.validators import InputRequired, NumberRange, URL


class DiscordChannelForm(FlaskForm):
    name = StringField("Name", validators=[InputRequired()])
    webhook_url = StringField("Webhook URL", validators=[InputRequired(), URL()])
    enabled = BooleanField("Enabled")
    cooldown_minutes = IntegerField("Cooldown (minutes)", validators=[InputRequired(), NumberRange(min=0, max=10080)],
                                    default=30)
    servers = SelectMultipleField("Game servers", coerce=int)
    groups = SelectMultipleField("Watched player groups", coerce=int)
    players = SelectMultipleField("Additional individual players")


class DiscordPlayerGroupForm(FlaskForm):
    name = StringField("Group name", validators=[InputRequired()])
    players = SelectMultipleField("Players")
