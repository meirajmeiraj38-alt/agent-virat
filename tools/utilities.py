"""Local utility tools for time, reminders, contacts, and DNC management."""

from datetime import datetime
from typing import Any

from pydantic import Field

from tools.base import RiskLevel, Tool, ToolContext, ToolInput


class EmptyInput(ToolInput):
    pass


class ReminderInput(ToolInput):
    text: str = Field(min_length=1, description="What to remember.")
    remind_at: datetime = Field(description="Reminder date and time in ISO 8601 format.")


class SearchContactsInput(ToolInput):
    query: str = Field(min_length=1, description="Name, group, language, phone, or email.")


class DoNotContactInput(ToolInput):
    recipient: str = Field(min_length=1, description="Contact name, email, or phone.")
    reason: str = Field(min_length=1, description="Why messages must not be sent.")


class PreferenceInput(ToolInput):
    key: str = Field(min_length=1, description="Preference name.")
    value: str = Field(min_length=1, description="Preference to remember.")


class GetCurrentDatetime(Tool):
    name = "get_current_datetime"
    description = "Get the current local date, time, and timezone."
    input_model = EmptyInput
    risk = RiskLevel.LOW

    def execute(self, arguments: dict[str, Any], context: ToolContext) -> dict[str, str]:
        self.input_model.model_validate(arguments)
        return {"datetime": datetime.now().astimezone().isoformat()}


class SetReminder(Tool):
    name = "set_reminder"
    description = "Save a local reminder for a specified date and time."
    input_model = ReminderInput
    risk = RiskLevel.MEDIUM

    def execute(self, arguments: dict[str, Any], context: ToolContext) -> dict[str, Any]:
        data = self.input_model.model_validate(arguments)
        reminder_id = context.memory.add_reminder(data.text, data.remind_at)
        return {
            "status": "saved",
            "reminder_id": reminder_id,
            "text": data.text,
            "remind_at": data.remind_at.isoformat(),
        }


class SearchContacts(Tool):
    name = "search_contacts"
    description = "Search Meiraj's locally saved contacts."
    input_model = SearchContactsInput
    risk = RiskLevel.LOW

    def execute(self, arguments: dict[str, Any], context: ToolContext) -> dict[str, Any]:
        data = self.input_model.model_validate(arguments)
        return {"contacts": context.memory.search_contacts(data.query)}


class AddDoNotContact(Tool):
    name = "add_do_not_contact"
    description = "Prevent future outbound messages to a recipient."
    input_model = DoNotContactInput
    risk = RiskLevel.MEDIUM

    def execute(self, arguments: dict[str, Any], context: ToolContext) -> dict[str, str]:
        data = self.input_model.model_validate(arguments)
        context.memory.add_do_not_contact(data.recipient, data.reason)
        return {"status": "saved", "recipient": data.recipient}


class GetPreferences(Tool):
    name = "get_preferences"
    description = "Read Meiraj's saved long-term preferences."
    input_model = EmptyInput
    risk = RiskLevel.LOW

    def execute(self, arguments: dict[str, Any], context: ToolContext) -> dict[str, Any]:
        self.input_model.model_validate(arguments)
        return {"preferences": context.memory.get_preferences()}


class SavePreference(Tool):
    name = "save_preference"
    description = "Save a long-term preference for future conversations."
    input_model = PreferenceInput
    risk = RiskLevel.MEDIUM

    def execute(self, arguments: dict[str, Any], context: ToolContext) -> dict[str, str]:
        data = self.input_model.model_validate(arguments)
        context.memory.set_preference(data.key, data.value)
        return {"status": "saved", "key": data.key}
