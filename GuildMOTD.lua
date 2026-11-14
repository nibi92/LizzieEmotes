-- MOTDs bypass CHAT_MSG_GUILD. Only change their local display, never the
-- guild API return value or the edit box used to save the message.
local issecretvalue = issecretvalue or function() return false end
local hookedDisplays = setmetatable({}, { __mode = "k" })
local hookedChats = setmetatable({}, { __mode = "k" })

local function ReplaceMOTD(text, plainDisplay)
	if issecretvalue(text) or type(text) ~= "string" then return text end
	if not Emoticons_Settings.CHAT_MSG_GUILD then return text end
	-- Also avoids processing our own output again during animation updates.
	if text:find("|T", 1, true) then return text end
	local rendered = Emoticons_RunReplacement(text, nil, nil, true)
	if plainDisplay then
		-- SimpleHTML and the Classic MOTD label do not handle emote links.
		rendered = rendered:gsub("|Htel:.-|h(.-)|h", "%1")
	end
	return rendered
end

local function HookDisplay(display)
	if not display or hookedDisplays[display] then return end
	hookedDisplays[display] = true
	local updating = false
	hooksecurefunc(display, "SetText", function(self, text)
		if updating then return end
		local rendered = ReplaceMOTD(text, true)
		if not issecretvalue(text) and rendered ~= text then
			updating = true
			self:SetText(rendered, true) -- Keep SimpleHTML's ignore-markup flag.
			updating = false
		end
	end)
	if display.GetText then
		local text = display:GetText()
		if not issecretvalue(text) and type(text) == "string" then display:SetText(text) end
	end
end

local function HookChat(frame)
	if not frame or hookedChats[frame] then return end
	hookedChats[frame] = true
	local addMessage = frame.AddMessage
	frame.AddMessage = function(self, text, ...)
		if not issecretvalue(text) and type(text) == "string" and GUILD_MOTD_TEMPLATE then
			local before, after = GUILD_MOTD_TEMPLATE:match("^(.-)%%s(.-)$")
			if before and #text >= #before + #after and text:sub(1, #before) == before
				and (#after == 0 or text:sub(-#after) == after) then
				local motd = text:sub(#before + 1, #text - #after)
				text = before .. ReplaceMOTD(motd) .. after
			end
		end
		return addMessage(self, text, ...)
	end
end

local function Setup()
	HookDisplay(GuildFrameNotesText) -- Classic guild roster.
	local guildInfo = CommunitiesFrame and CommunitiesFrame.GuildDetailsFrame
	local info = guildInfo and guildInfo.Info
	HookDisplay(info and info.MOTDScrollFrame and info.MOTDScrollFrame.MOTD)
	for _, name in ipairs(CHAT_FRAMES or {}) do HookChat(_G[name]) end
end

local events = CreateFrame("Frame")
events:RegisterEvent("ADDON_LOADED")
events:RegisterEvent("PLAYER_LOGIN")
events:RegisterEvent("UPDATE_CHAT_WINDOWS")
events:RegisterEvent("UPDATE_FLOATING_CHAT_WINDOWS")
events:SetScript("OnEvent", function()
	Setup()
	-- Guild UI can be loaded on demand; hook the actual instance passed by
	-- Blizzard as well as looking up frames that already exist.
	if CommunitiesGuildInfoFrame_UpdateText and not events.hookedGuildInfo then
		events.hookedGuildInfo = true
		hooksecurefunc("CommunitiesGuildInfoFrame_UpdateText", function(self)
			HookDisplay(self.MOTDScrollFrame and self.MOTDScrollFrame.MOTD)
			local getMOTD = C_GuildInfo and C_GuildInfo.GetMOTD or GetGuildRosterMOTD
			if getMOTD then
				local display = self.MOTDScrollFrame and self.MOTDScrollFrame.MOTD
				if display then display:SetText(getMOTD(), true) end
			end
		end)
	end
end)

function Emoticons_AnimateGuildMOTD()
	for display in pairs(hookedDisplays) do
		if display:IsShown() then
			if display:IsObjectType("FontString") then
				TwitchEmotesAnimator_UpdateEmoteInFontString(display, 28, 28)
			else
				for _, region in ipairs({display:GetRegions()}) do
					if region:IsObjectType("FontString") then
						TwitchEmotesAnimator_UpdateEmoteInFontString(region, 28, 28)
					end
				end
			end
		end
	end
end
