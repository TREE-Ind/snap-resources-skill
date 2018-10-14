from mycroft import MycroftSkill, intent_file_handler
from mycroft.skills.core import MycroftSkill
from mycroft.util.log import getLogger
from mycroft.audio import wait_while_speaking
from mycroft.skills.context import *
from twilio.rest import Client

import time

class MessageLog(Object):
    def __init__(self, message='', seperator='\n'):
        self.body = message
        self.prefixes = {}
        self.suffixes = {}
        self.params = {}
        self.seperator = seperator

    def add_line(self, data=None, prefix='', suffix=''):
        if not data:
            data = {}

        self.params.update(data)
        for key, value in data:
            self.prefixes.update({
                key: prefix
            })
            self.suffixes.update({
                key: suffix
            })

    def __str__(self):
        lines = [(self.prefixes[x], self.params[x], self.suffixes[x]) for x in self.params.keys()]
        return self.seperator.join(["{}{}{}".format(prefix, value, suffix) for prefix, value, suffix in lines])



class SnapResourceSkill(MycroftSkill):
    '''
        This skill has a dialogue for determining snap eligibility.

        Where can I go for more snap info?

        Am I eligible for food stamps?
    '''
    USEFUL_SNAP_LINKS = {
        'am_i_eligible': 'https://www.fns.usda.gov/snap/eligibility',
        'how_to_apply': 'https://www.fns.usda.gov/snap/apply',
        'state_information': 'https://www.fns.usda.gov/snap/snap-application-and-local-office-locators',
        'when_are_benefits_available': 'https://www.fns.usda.gov/snap/snap-monthly-benefit-issuance-schedule',
        'what_can_snap_buy': 'https://www.fns.usda.gov/snap/eligible-food-items',
        'where_can_i_use_snap_ebt': 'https://www.fns.usda.gov/snap/retailerlocator'
    }

    def __init__(self):
        MycroftSkill.__init__(self)
        self._client = None
        self.message_log = MessageLog()

    def try_load_client(self):
        if not self.settings.get("twilio_integration_enabled"):
            return None

        if not self._client:
            if self.settings.get('twilio_account_sid') and self.settings.get('twilio_auth_token'):
                self._client = Client(self.settings.get('twilio_account_sid'), self.settings.get('twilio_auth_token'))

        return self._client

    @intent_file_handler('snap.eligibility.intent')
    def handle_resources_snap(self, message):
        is_yes = lambda x: (x == "yes")
        is_no = lambda x: (x == "no")
        self.speak_dialog('intro.snap.eligibility')
        wait_while_speaking()

        time.sleep(5)
        eligibility_info = self.ask_yesno('ask.snap.eligibility.detailed')
        wait_while_speaking()

        if is_yes(eligibility_info):
            if self.settings.get('twilio_integration_enabled') and self.try_load_client():
                self.record_info = self.ask_yesno('text')
            else:
                self.record_info = "no"

            if is_yes(self.record_info):
                self.speak_dialog('success')
                self.speak_dialog('intro.collect.information')
                time.sleep(3)

                self.name = self.get_response('ask.name')
                wait_while_speaking()

                self.message_log.add_line({ "introduction_name": self.name }, 'Hi ', ", this is Ezra. I'm sending along some useful information!" )

                self.phone_number = self.get_response('ask.phone.number')
                wait_while_speaking()

            self.citizen = self.ask_yesno('citizen')
            wait_while_speaking()
            if is_no(self.citizen):
                self.five_years = self.ask_yesno('five.years')
                wait_while_speaking()

            if is_yes(self.citizen) or is_yes(self.five_years):
                self.employment = self.ask_yesno('employment')
                wait_while_speaking()
                if is_yes(self.employment):
                    self.income = self.ask_yesno('income')
                    wait_while_speaking()

                    if is_yes(self.income):
                        self.inquire_more = True
                        self.speak_dialog('generic.yes')
                    else:
                        self.inquire_more = False
                        self.speak_dialog('generic.no')

            if is_yes(self.record_info) and self.phone_number:

                if self.inquire_more:
                    useful_links = (
                        self.USEFUL_SNAP_LINKS['am_i_eligible'],
                        self.USEFUL_SNAP_LINKS['how_to_apply'],
                        self.USEFUL_SNAP_LINKS['state_information'],
                        self.USEFUL_SNAP_LINKS['when_are_benefits_available'],
                        self.USEFUL_SNAP_LINKS['what_can_snap_buy'],
                        self.USEFUL_SNAP_LINKS['where_can_i_use_snap_ebt']
                    )
                else:
                    useful_links = (
                        self.USEFUL_SNAP_LINKS['am_i_eligible'],
                        self.USEFUL_SNAP_LINKS['state_information']
                    )

                for idx, link in enumerate(useful_links, start=1):
                    line_id = 'useful_link_{}'.format(idx)
                    self.message_log.add_line({line_id: link}, "{}:".format(idx), "")

                    client = self.try_load_client()

                if client:
                    messageid = client.messages.create(from_=self.settings.get('twilio_from_number'), to=self.phone_number, body=str(self.message_log))

        else:
            self.speak_dialog('here.to.assist')
            wait_while_speaking()



def create_skill():
    return SnapResourceSkill()
