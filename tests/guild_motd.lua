-- Run from the repository root with Lua 5.1+.
local function noop() end
LibStub = { GetLibrary = noop }
ItemTextPageText = { SetText = noop }
OpenMailBodyText = { SetText = noop }
ItemRefTooltip = { SetHyperlink = noop }
EventRegistry = { RegisterCallback = noop }
SendMail = noop
getfenv = getfenv or function() return _G end
dofile("LizzieEmotes.lua")
TwitchEmotes_emoticons = { [":wave:"] = "wave" }
TwitchEmotes_defaultpack = { wave = "Interface\\AddOns\\LizzieEmotes\\Emotes\\wave.tga:28:28" }
TwitchEmoteStatistics = {}
TwitchEmotes_GetAnimData = noop
UnitGUID = function() return "player" end
for i = 1, 20 do
	local name = debug.getupvalue(Emoticons_InsertEmoticons, i)
	if name == "accept_stat_updates" then debug.setupvalue(Emoticons_InsertEmoticons, i, true) end
end

local events
CreateFrame = function()
	events = { RegisterEvent = noop, SetScript = function(self, _, fn) self.onEvent = fn end }
	return events
end
function hooksecurefunc(object, method, callback)
	if type(object) == "string" then object, method, callback = _G, object, method end
	local original = object[method]
	object[method] = function(...)
		local result = original(...)
		callback(...)
		return result
	end
end
local function label(text)
	return {
		text = text,
		GetText = function(self) return self.text end,
		SetText = function(self, value, ignoreMarkup) self.text, self.ignoreMarkup = value, ignoreMarkup end,
		IsShown = function() return true end,
		IsObjectType = function(_, kind) return kind == "FontString" end,
	}
end
GuildFrameNotesText = label("Hello :wave:")
local messages = {}
ChatFrame1 = { AddMessage = function(self, text, ...)
	messages[#messages + 1] = { text, ... }
	return "forwarded"
end }
CHAT_FRAMES = { "ChatFrame1" }
GUILD_MOTD_TEMPLATE = "Guild Message of the Day: %s"
local secret = {}
issecretvalue = function(value) return value == secret end
dofile("GuildMOTD.lua")
events.onEvent()
assert(GuildFrameNotesText.text:find("|T", 1, true))
assert(not GuildFrameNotesText.text:find("|H", 1, true))
assert(next(TwitchEmoteStatistics) == nil, "MOTD counted as chat")
local rendered = GuildFrameNotesText.text
GuildFrameNotesText:SetText(rendered)
assert(GuildFrameNotesText.text == rendered, "display hook processed its own output")
assert(ChatFrame1:AddMessage("Guild Message of the Day: :wave:", 1, 2, 3) == "forwarded")
assert(messages[1][1]:find("|T", 1, true) and messages[1][2] == 1 and messages[1][4] == 3)
ChatFrame1:AddMessage("Ordinary :wave:")
assert(messages[2][1] == "Ordinary :wave:")
ChatFrame1:AddMessage(secret)
assert(messages[3][1] == secret)
GuildFrameNotesText:SetText(secret)
assert(GuildFrameNotesText.text == secret)
Emoticons_Settings.CHAT_MSG_GUILD = false
GuildFrameNotesText:SetText(":wave:")
assert(GuildFrameNotesText.text == ":wave:")
ChatFrame1:AddMessage("Guild Message of the Day: :wave:")
assert(messages[4][1] == "Guild Message of the Day: :wave:")
Emoticons_Settings.CHAT_MSG_GUILD = true

-- A newly discovered SimpleHTML without GetText is rendered on its next update.
local html = { SetText = label().SetText }
local info = { MOTDScrollFrame = { MOTD = html } }
local blizzardUpdating = false
C_GuildInfo = { GetMOTD = function()
	assert(blizzardUpdating, "addon called protected GetMOTD")
	return ":wave:"
end }
GetGuildRosterMOTD = function() error("addon called legacy MOTD API") end
CommunitiesGuildInfoFrame_UpdateText = function(self)
	blizzardUpdating = true
	self.MOTDScrollFrame.MOTD:SetText(C_GuildInfo.GetMOTD(), true)
	blizzardUpdating = false
end
events.onEvent()
CommunitiesGuildInfoFrame_UpdateText(info)
assert(html.text == ":wave:")
CommunitiesGuildInfoFrame_UpdateText(info)
assert(html.text:find("|T", 1, true) and html.ignoreMarkup == true)
assert(not html.text:find("|H", 1, true))
html:SetText("Updated :wave:", true)
assert(html.text:find("|T", 1, true))

-- Normal load-on-demand setup hooks the display before Blizzard's first update.
local loadedHTML = { SetText = label().SetText }
local loadedInfo = { MOTDScrollFrame = { MOTD = loadedHTML } }
CommunitiesFrame = { GuildDetailsFrame = { Info = loadedInfo } }
events.onEvent()
CommunitiesGuildInfoFrame_UpdateText(loadedInfo)
assert(loadedHTML.text:find("|T", 1, true) and loadedHTML.ignoreMarkup == true)

-- New chat windows and repeated setup must preserve one message per call.
ChatFrame2 = { AddMessage = ChatFrame1.AddMessage }
CHAT_FRAMES[2] = "ChatFrame2"
events.onEvent()
events.onEvent()
local count = #messages
ChatFrame2:AddMessage("Guild Message of the Day: :wave:")
assert(#messages == count + 1)
assert(next(TwitchEmoteStatistics) == nil)

-- Rendering MOTDs must not interrupt duplicate chat-message statistics.
Emoticons_RunReplacement(":wave:", "other", 12)
assert(TwitchEmoteStatistics.wave[3] == 1)
html:SetText(":wave:", true)
Emoticons_RunReplacement(":wave:", "other", 12)
assert(TwitchEmoteStatistics.wave[3] == 1)
print("Guild MOTD regression checks passed")
