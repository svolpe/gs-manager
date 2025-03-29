from flask_wtf import FlaskForm
from flask_wtf import FlaskForm
from wtforms import StringField, FieldList, SelectField, RadioField, IntegerField, SelectMultipleField, FormField
from wtforms.validators import InputRequired, NumberRange

class ServerConfiguration(FlaskForm):
    server_name = StringField("Server Name", validators=[InputRequired()])
    max_players = IntegerField("Max Players", validators=[NumberRange(min=1, max=100), InputRequired()])
    min_level = IntegerField("Min Level", validators=[NumberRange(min=1, max=40), InputRequired()])
    max_level = IntegerField("Max Level", validators=[NumberRange(min=1, max=40), InputRequired()])
    pause_play = SelectField("Pause And Play", choices=[(0, 'Game only can be paused by DM'),
                                                        (1, 'Game can be paused by players')],
                            validators=[InputRequired()])
    pvp = SelectField("PVP", choices=[(0, 'None'), (1, 'Party'), (2, 'Full')], validators=[InputRequired()])
    server_vault = SelectField("Server Vault", choices=[(0, 'Local Characters Only'), (1, 'Server Characters Only')],
                            validators=[InputRequired()])
    enforce_legal_char = RadioField('Enforce Legal Characters', choices=[(1, 'Yes'), (0, 'No'), ],
                                    validators=[InputRequired()])
    item_lv_restrictions = RadioField('Item Level Restrictions', choices=[(1, 'Yes'), (0, 'No')],
                                    validators=[InputRequired()])
    game_type = SelectField("Game Type", choices=[(0, 'Action'), (1, 'Story'), (2, 'Story Lite'), (3, 'Role Play'),
                                                (4, 'Team'), (5, 'Melee'), (6, 'Arena'), (7, 'Social'),
                                                (8, 'Alternative'), (9, 'PW Action'), (10, 'PW Story'), (11, 'Solo'),
                                                (12, 'Tech Support')], validators=[InputRequired()])
    one_party = SelectField("One Party", choices=[(0, 'Allow multiple parties'), (1, 'Only allow one party')],
                            validators=[InputRequired()])
    difficulty = SelectField("Difficulty", choices=[(1, 'Easy'), (2, 'Normal'), (3, 'D&D Hardcore'),
                                                    (4, 'Very Difficult')], validators=[InputRequired()])
    auto_save_interval = IntegerField("Auto Save Interval", validators=[InputRequired()])
    player_pwd = StringField("Player Password")
    dm_pwd = StringField("DM Password")
    admin_pwd = StringField("Admin Password")
    module_name = SelectField("Select a Module", choices=[("DockerDemo", "DockerDemo"), ], validators=[InputRequired()])
    port = IntegerField("Port (5121)", validators=[NumberRange(min=5120, max=5170), InputRequired()])
    public_server = SelectField("Public Server", choices=[(0, 'Not Public'), (1, 'Public')],
                                validators=[InputRequired()])
    reload_when_empty = RadioField('Reload When Empty', choices=[(1, 'Yes'), (0, 'No')], validators=[InputRequired()])
    volumes = SelectMultipleField()
    database = RadioField('Use SQL Database?', choices=[('yes', 'Yes'), ('no', 'No')], validators=[InputRequired()])
    is_active = RadioField('Server Activate?', choices=[(1, 'Yes'), (0, 'No')], validators=[InputRequired()])


class ServerConfigDynamic(FlaskForm):
    configuration = FieldList(FormField(ServerConfiguration), min_entries=0)