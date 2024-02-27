let SessionLoad = 1
let s:so_save = &g:so | let s:siso_save = &g:siso | setg so=0 siso=0 | setl so=-1 siso=-1
let v:this_session=expand("<sfile>:p")
let EasyMotion_off_screen_search =  1 
let EasyMotion_move_highlight =  1 
let EasyMotion_use_migemo =  0 
let EasyMotion_smartcase =  1 
let EasyMotion_hl_group_target = "EasyMotionTarget"
let DevIconsEnableFoldersOpenClose =  0 
let EasyMotion_enter_jump_first =  0 
let EasyMotion_use_upper =  0 
let EasyMotion_do_mapping =  0 
let WebDevIconsNerdTreeAfterGlyphPadding = " "
let DevIconsEnableDistro =  1 
let WebDevIconsUnicodeDecorateFileNodes =  1 
let DevIconsEnableFolderPatternMatching =  1 
let EasyMotion_space_jump_first =  0 
let EasyMotion_prompt = "Search for {n} character(s): "
let EasyMotion_use_regexp =  1 
let WebDevIconsUnicodeDecorateFolderNodesDefaultSymbol = ""
let WebDevIconsTabAirLineAfterGlyphPadding = ""
let TabbyTabNames = "[]"
let DevIconsArtifactFixChar = " "
let EasyMotion_show_prompt =  1 
let EasyMotion_add_search_history =  1 
let EasyMotion_do_shade =  1 
let EasyMotion_grouping =  1 
let WebDevIconsUnicodeDecorateFileNodesDefaultSymbol = ""
let EasyMotion_inc_highlight =  1 
let NERDTreeGitStatusUpdateOnCursorHold =  1 
let EasyMotion_skipfoldedline =  1 
let EasyMotion_hl_move = "EasyMotionMoveHL"
let WebDevIconsUnicodeDecorateFolderNodesExactMatches =  1 
let EasyMotion_hl_group_shade = "EasyMotionShade"
let WebDevIconsUnicodeByteOrderMarkerDefaultSymbol = ""
let WebDevIconsNerdTreeGitPluginForceVAlign =  1 
let DevIconsAppendArtifactFix =  0 
let EasyMotion_ignore_exception =  0 
let EasyMotion_re_line_anywhere = "\\v(<.|^$)|(.>|^$)|(\\l)\\zs(\\u)|(_\\zs.)|(#\\zs.)"
let WebDevIconsUnicodeDecorateFolderNodes =  1 
let EasyMotion_re_anywhere = "\\v(<.|^$)|(.>|^$)|(\\l)\\zs(\\u)|(_\\zs.)|(#\\zs.)"
let WebDevIconsNerdTreeBeforeGlyphPadding = " "
let EasyMotion_verbose =  1 
let WebDevIconsUnicodeGlyphDoubleWidth =  1 
let WebDevIconsUnicodeDecorateFolderNodesSymlinkSymbol = ""
let EasyMotion_hl2_first_group_target = "EasyMotionTarget2First"
let EasyMotion_hl_inc_search = "EasyMotionIncSearch"
let EasyMotion_cursor_highlight =  1 
let EasyMotion_hl2_second_group_target = "EasyMotionTarget2Second"
let EasyMotion_startofline =  1 
let NERDTreeUpdateOnCursorHold =  1 
let DevIconsDefaultFolderOpenSymbol = ""
let EasyMotion_keys = "asdghklqwertyuiopzxcvbnmfj;"
let DevIconsEnableFolderExtensionPatternMatching =  0 
let EasyMotion_force_csapprox =  0 
let EasyMotion_loaded =  1 
let EasyMotion_hl_inc_cursor = "EasyMotionIncCursor"
let EasyMotion_disable_two_key_combo =  0 
let WebDevIconsTabAirLineBeforeGlyphPadding = " "
let EasyMotion_landing_highlight =  0 
silent only
silent tabonly
cd ~/Projects/WanaLyzer3.0
if expand('%') == '' && !&modified && line('$') <= 1 && getline(1) == ''
  let s:wipebuf = bufnr('%')
endif
let s:shortmess_save = &shortmess
if &shortmess =~ 'A'
  set shortmess=aoOA
else
  set shortmess=aoO
endif
badd +1 sample/window.py
badd +6 widgets/utils.py
argglobal
%argdel
$argadd sample/window.py
$argadd widgets/utils.py
edit widgets/utils.py
let s:save_splitbelow = &splitbelow
let s:save_splitright = &splitright
set splitbelow splitright
wincmd _ | wincmd |
vsplit
1wincmd h
wincmd w
let &splitbelow = s:save_splitbelow
let &splitright = s:save_splitright
wincmd t
let s:save_winminheight = &winminheight
let s:save_winminwidth = &winminwidth
set winminheight=0
set winheight=1
set winminwidth=0
set winwidth=1
wincmd =
argglobal
if bufexists(fnamemodify("widgets/utils.py", ":p")) | buffer widgets/utils.py | else | edit widgets/utils.py | endif
if &buftype ==# 'terminal'
  silent file widgets/utils.py
endif
balt sample/window.py
setlocal fdm=manual
setlocal fde=0
setlocal fmr={{{,}}}
setlocal fdi=#
setlocal fdl=0
setlocal fml=1
setlocal fdn=20
setlocal fen
silent! normal! zE
let &fdl = &fdl
let s:l = 6 - ((5 * winheight(0) + 47) / 94)
if s:l < 1 | let s:l = 1 | endif
keepjumps exe s:l
normal! zt
keepjumps 6
normal! 0
wincmd w
argglobal
if bufexists(fnamemodify("sample/window.py", ":p")) | buffer sample/window.py | else | edit sample/window.py | endif
if &buftype ==# 'terminal'
  silent file sample/window.py
endif
balt widgets/utils.py
setlocal fdm=manual
setlocal fde=0
setlocal fmr={{{,}}}
setlocal fdi=#
setlocal fdl=0
setlocal fml=1
setlocal fdn=20
setlocal fen
silent! normal! zE
let &fdl = &fdl
let s:l = 1 - ((0 * winheight(0) + 47) / 94)
if s:l < 1 | let s:l = 1 | endif
keepjumps exe s:l
normal! zt
keepjumps 1
normal! 0
wincmd w
wincmd =
tabnext 1
if exists('s:wipebuf') && len(win_findbuf(s:wipebuf)) == 0 && getbufvar(s:wipebuf, '&buftype') isnot# 'terminal'
  silent exe 'bwipe ' . s:wipebuf
endif
unlet! s:wipebuf
set winheight=1 winwidth=20
let &shortmess = s:shortmess_save
let &winminheight = s:save_winminheight
let &winminwidth = s:save_winminwidth
let s:sx = expand("<sfile>:p:r")."x.vim"
if filereadable(s:sx)
  exe "source " . fnameescape(s:sx)
endif
let &g:so = s:so_save | let &g:siso = s:siso_save
set hlsearch
doautoall SessionLoadPost
unlet SessionLoad
" vim: set ft=vim :
