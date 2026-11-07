-- Run from the repository root with Lua 5.1+.
local function noop() end
EditBoxAutoCompleteBox = { SetScript = noop }
ChatEdit_GetNextTellTarget = noop
dofile("libs/Lib-EditBox-AutoComplete/Lib-EditBox-AutoComplete.lua")

local scripts, hooks = {}, {}
local inAddonHook = false
local originalCalls = 0
local function original()
    assert(not inAddonHook, "Blizzard handler called from addon code")
    originalCalls = originalCalls + 1
end
scripts.OnEditFocusLost = original
scripts.OnEscapePressed = original
local editbox = {
    GetScript = function(_, event) return scripts[event] end,
    SetScript = function(_, event, callback) scripts[event] = callback end,
    HookScript = function(_, event, callback) hooks[event] = callback end,
}
SetupAutoComplete(editbox, {}, 5, { useArrowButtons = false })
assert(scripts.OnEditFocusLost == original)
assert(scripts.OnEscapePressed == original)

local hidden, cleared = 0, 0
EditBoxAutoComplete_HideIfAttachedTo = function(box)
    assert(box == editbox)
    hidden = hidden + 1
end
EditBox_ClearHighlight = function(box)
    assert(box == editbox)
    cleared = cleared + 1
end
EditBoxAutoComplete_OnEscapePressed = function(box)
    EditBoxAutoComplete_HideIfAttachedTo(box)
end
local function fire(event)
    scripts[event](editbox)
    inAddonHook = true
    hooks[event](editbox)
    inAddonHook = false
end
fire("OnEditFocusLost")
assert(hidden == 1 and cleared == 1)
EditBoxAutoCompleteBox.mouseInside = true
fire("OnEditFocusLost")
assert(hidden == 1 and cleared == 1)
fire("OnEscapePressed")
assert(originalCalls == 3 and hidden == 2)

-- The popup must paint without querying dimensions or invoking backdrop math.
local popup = {}
local texture = {
    SetAllPoints = function(_, target) assert(target == popup) end,
    SetTexture = function(_, path) assert(path:find("Background%-Dark")) end,
}
popup.CreateTexture = function(_, _, layer)
    assert(layer == "BACKGROUND")
    return texture
end
AutoCompleteInstructions = { SetText = noop }
PRESS_TAB = "Press Tab"
EditBoxAutoComplete_OnLoad(popup)
assert(popup.background == texture)
print("Autocomplete regression checks passed")
