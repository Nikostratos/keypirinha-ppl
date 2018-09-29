import keypirinha as kp
import keypirinha_util as kpu
import json
import re
from pathlib import Path
import os
import sys

class Verb(object):
    name: str
    desc: str
    target: str
    item: str
    category: object
    action: object
    
    def __init__(self, name, desc, target, item, category, action):
        self.name = name
        self.desc = desc
        self.target = target
        self.item = item
        self.category = category
        self.action = action
    
class Ppl(kp.Plugin):
    # Attributes in the contacts json doc
    AD_ATTR_NAME = 'displayName'
    AD_ATTR_MAIL = 'mail'
    AD_ATTR_PHONE = 'telephoneNumber'
    AD_ATTR_MOBILE = 'mobile'
    AD_ATTR_TITLE = 'description'

    # Plugin actions
    ACTION_CALL_MOBILE = "call_mobile"
    ACTION_CALL_PHONE = "call_phone"
    ACTION_MAIL = "mail"
    ACTION_CARD = "card"
    ACTION_COPY = "copy"
    
    ITEMCAT_CALLEE_M = kp.ItemCategory.USER_BASE + 1
    ITEMCAT_CALLEE_P = kp.ItemCategory.USER_BASE + 2
    ITEMCAT_MAILEE = kp.ItemCategory.USER_BASE + 3
    ITEMCAT_CONTACT = kp.ItemCategory.USER_BASE + 4
    ITEMCATS = (ITEMCAT_CALLEE_M, ITEMCAT_CALLEE_P, ITEMCAT_MAILEE, ITEMCAT_CONTACT)

    ITEM_LABEL_PREFIX = "Ppl: "
    
    ID_ITEM = "displayName"
    
    VERB_LIST = [
        Verb('Info', 'Contact info',            'INFO', AD_ATTR_PHONE, ITEMCAT_CONTACT, ACTION_CARD),
        Verb('Mail', 'Mail contact',            'MAIL', AD_ATTR_MAIL, ITEMCAT_MAILEE, ACTION_MAIL),
        Verb('Call', 'Call contact on phone',   'CALL', AD_ATTR_PHONE, ITEMCAT_CALLEE_P, ACTION_CALL_PHONE),
        Verb('Cell', 'Call contact on mobile',  'CELL', AD_ATTR_MOBILE, ITEMCAT_CALLEE_M, ACTION_CALL_MOBILE)
    ]
    VERBS = { v.target: v for v in VERB_LIST}
    
    CONTACTS_FILE = "contacts.json"

    def __init__(self):
        super().__init__()

    def load_contacts(self):
        self.contacts = []
        contacts_file = os.path.join(kp.user_config_dir(), self.CONTACTS_FILE)
        try:
            
            if not os.path.exists(contacts_file):
                self.error(f"Contacts file {contacts_file} does not exist. Functionality is disabled.")
            with open(contacts_file, "r") as f:
                self.contacts = json.load(f)                 
        except Exception as exc:
            self.warn(f"Failed to load contacts file {contacts_file}, {exc}")
            return
    
    def on_start(self):
        self.settings = self.load_settings()
        
        self.load_contacts()
        
        call_mobile_action = self.create_action(
                name=self.ACTION_CALL_MOBILE,
                label="Call mobile",
                short_desc="Call the mobile number",
                data_bag = self.AD_ATTR_MOBILE)

        call_phone_action = self.create_action(
                name = self.ACTION_CALL_PHONE,
                label = "Call phone",
                short_desc = "Call the phone number",
                data_bag = self.AD_ATTR_PHONE)
                
        mail_action = self.create_action(
                name=self.ACTION_MAIL,
                label="Send mail",
                short_desc="Send a mail to the contact",
                data_bag = self.AD_ATTR_MAIL)
                
        card_action = self.create_action(
                name=self.ACTION_CARD,
                label="Copy contact",
                short_desc="Copy contact information to clipboard")
                
        copy_action = self.create_action(
                name=self.ACTION_COPY,
                label="Copy item",
                short_desc="Copy looked up item")
                
        self.set_actions(self.ITEMCAT_CALLEE_M, [call_mobile_action, call_phone_action, copy_action, card_action]) 
        self.set_actions(self.ITEMCAT_CALLEE_P, [call_phone_action, call_mobile_action, copy_action, card_action]) 
        self.set_actions(self.ITEMCAT_MAILEE,   [mail_action, copy_action, card_action]) 
        self.set_actions(self.ITEMCAT_CONTACT,  [card_action, copy_action]) 

    def on_activated(self):
        pass

    def on_deactivated(self):
        pass

    def on_events(self, flags):
        if flags & kp.Events.PACKCONFIG:
            self.load_contacts()
            self.on_catalog()
        
    def on_catalog(self):
        catalog = [
            self.create_item(
                    category = kp.ItemCategory.REFERENCE,
                    label = self.ITEM_LABEL_PREFIX + v.name,
                    short_desc = v.desc,
                    target = v.target,
                    args_hint = kp.ItemArgsHint.REQUIRED,
                    hit_hint = kp.ItemHitHint.NOARGS)
            for v in self.VERB_LIST
        ]
        '''        
        for name,measure in self.measures.items():
            catalog.append(self.create_item(
                category=kp.ItemCategory.REFERENCE,
                label=self.ITEM_LABEL_PREFIX + measure["name"],
                short_desc=measure["desc"],
                target=measure["name"],
                args_hint=kp.ItemArgsHint.REQUIRED,
                hit_hint=kp.ItemHitHint.NOARGS))

        if self.customized_config:
            catalog.append(self.create_item(
                category=self.ITEMCAT_RELOAD_DEFS,
                label=self.ITEM_LABEL_PREFIX + "Reload definitions",
                short_desc="Reload the custom definition file",
                target=measure["name"],
                args_hint=kp.ItemArgsHint.FORBIDDEN,
                hit_hint=kp.ItemHitHint.NOARGS))
        '''
        self.set_catalog(catalog)
       
    def on_suggest(self, user_input, items_chain):
        if not items_chain or not user_input:
            return

        current_item = items_chain[-1]
        verb = self.VERBS[current_item.target()]
        suggestions = []

        for idx, contact in enumerate(self.contacts):
            if (not (verb.item in contact) or 
                not (self.ID_ITEM in contact) or
                not contact[self.ID_ITEM]):
                continue
            
            if len(suggestions) > 10:
                break
                
            item = contact[verb.item]
            if not item or not user_input.lower() in contact[self.ID_ITEM].lower():
                continue

            title = contact[self.AD_ATTR_TITLE] if self.AD_ATTR_TITLE in contact else ""
            suggestions.append(self.create_item(
                category=verb.category,
                label=f'{verb.name} {contact[self.ID_ITEM]} - {contact[verb.item]}',
                short_desc=f"{self.AD_ATTR_TITLE}",
                target=item,
                args_hint=kp.ItemArgsHint.REQUIRED,
                hit_hint=kp.ItemHitHint.IGNORE,
                data_bag=kpu.kwargs_encode(verb=verb.target, contact_no=idx)))
        self.set_suggestions(suggestions, kp.Match.ANY, kp.Sort.NONE)

    def do_card_action(self, contact):
        text = f"Name\t{contact[self.AD_ATTR_NAME]}"
        
        if contact[self.AD_ATTR_MAIL]:
            text += f"\nMail\t{contact[self.AD_ATTR_MAIL]}"
        if contact[self.AD_ATTR_PHONE]:
            text += f"\nPhone#\t{contact[self.AD_ATTR_PHONE]}"
        if contact[self.AD_ATTR_MOBILE]:
            text += f"\nMobile#\t{contact[self.AD_ATTR_MOBILE]}"
        if contact[self.AD_ATTR_TITLE]:
            text += f"\nTitle#\t{contact[self.AD_ATTR_TITLE]}"

        kpu.set_clipboard(text)

    def do_call_action(self, contact, verb):
        url = f"tel:{contact[verb.item]}".replace(" ", "")
        kpu.shell_execute(url, args='', working_dir='', verb='', try_runas=True, detect_nongui=True, api_flags=None, terminal_cmd=None, show=-1)
    
    def do_mail_action(self, contact, verb):
        url = f"mailto:{contact[verb.item]}"
        kpu.shell_execute(url, args='', working_dir='', verb='', try_runas=True, detect_nongui=True, api_flags=None, terminal_cmd=None, show=-1)
    
    def on_execute(self, item, action):
        if (not item) or (not item.category()) in self.ITEMCATS:
            return

        params = kpu.kwargs_decode(item.data_bag())
        verb = self.VERBS[params['verb']]
        contact_no = int(params['contact_no'])
        contact = self.contacts[contact_no]
        
        action_name = action.name() if action else verb.action

        if action_name == self.ACTION_CALL_MOBILE:
            self.do_call_action(contact, verb)
        elif action_name == self.ACTION_CALL_PHONE:
            self.do_call_action(contact, verb)
        elif action_name == self.ACTION_MAIL:
            self.do_mail_action(contact, verb)
        elif action_name == self.ACTION_CARD:
            self.do_card_action(contact)
        elif action_name == self.ACTION_COPY:
            kpu.set_clipboard(contact[verb.item])