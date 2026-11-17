"""Central registration point for all available tools."""

from tools.base import Tool
from tools.email_tool import ReadRecentEmails, SendEmail
from tools.facebook import CreateFacebookPost, ReplyFacebookComment
from tools.utilities import (
    AddDoNotContact,
    GetCurrentDatetime,
    GetPreferences,
    SavePreference,
    SearchContacts,
    SetReminder,
)
from tools.whatsapp import GetContacts, SendWhatsAppMessage


def build_tools() -> list[Tool]:
    """Create the tool set exposed to Claude."""
    return [
        SendWhatsAppMessage(),
        GetContacts(),
        SendEmail(),
        ReadRecentEmails(),
        CreateFacebookPost(),
        ReplyFacebookComment(),
        GetCurrentDatetime(),
        SetReminder(),
        SearchContacts(),
        AddDoNotContact(),
        GetPreferences(),
        SavePreference(),
    ]
