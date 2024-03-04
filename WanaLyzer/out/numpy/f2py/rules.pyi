from . import __version__ as __version__, capi_maps as capi_maps, cfuncs as cfuncs, common_rules as common_rules, f90mod_rules as f90mod_rules, func2subr as func2subr, use_rules as use_rules
from .auxfuncs import applyrules as applyrules, debugcapi as debugcapi, dictappend as dictappend, errmess as errmess, gentitle as gentitle, getargs2 as getargs2, hascallstatement as hascallstatement, hasexternals as hasexternals, hasinitvalue as hasinitvalue, hasnote as hasnote, hasresultnote as hasresultnote, isarray as isarray, isarrayofstrings as isarrayofstrings, isattr_value as isattr_value, ischaracter as ischaracter, ischaracter_or_characterarray as ischaracter_or_characterarray, ischaracterarray as ischaracterarray, iscomplex as iscomplex, iscomplexarray as iscomplexarray, iscomplexfunction as iscomplexfunction, iscomplexfunction_warn as iscomplexfunction_warn, isdummyroutine as isdummyroutine, isexternal as isexternal, isfunction as isfunction, isfunction_wrap as isfunction_wrap, isint1 as isint1, isint1array as isint1array, isintent_aux as isintent_aux, isintent_c as isintent_c, isintent_callback as isintent_callback, isintent_copy as isintent_copy, isintent_hide as isintent_hide, isintent_inout as isintent_inout, isintent_nothide as isintent_nothide, isintent_out as isintent_out, isintent_overwrite as isintent_overwrite, islogical as islogical, islong_complex as islong_complex, islong_double as islong_double, islong_doublefunction as islong_doublefunction, islong_long as islong_long, islong_longfunction as islong_longfunction, ismoduleroutine as ismoduleroutine, isoptional as isoptional, isrequired as isrequired, isscalar as isscalar, issigned_long_longarray as issigned_long_longarray, isstring as isstring, isstringarray as isstringarray, isstringfunction as isstringfunction, issubroutine as issubroutine, issubroutine_wrap as issubroutine_wrap, isthreadsafe as isthreadsafe, isunsigned as isunsigned, isunsigned_char as isunsigned_char, isunsigned_chararray as isunsigned_chararray, isunsigned_long_long as isunsigned_long_long, isunsigned_long_longarray as isunsigned_long_longarray, isunsigned_short as isunsigned_short, isunsigned_shortarray as isunsigned_shortarray, l_and as l_and, l_not as l_not, l_or as l_or, outmess as outmess, replace as replace, requiresf90wrapper as requiresf90wrapper, stripcomma as stripcomma
from _typeshed import Incomplete

f2py_version: Incomplete
numpy_version: Incomplete
options: Incomplete
sepdict: Incomplete
generationtime: Incomplete
module_rules: Incomplete
defmod_rules: Incomplete
routine_rules: Incomplete
rout_rules: Incomplete
typedef_need_dict: Incomplete
aux_rules: Incomplete
arg_rules: Incomplete
check_rules: Incomplete

def buildmodule(m, um): ...

stnd: Incomplete

def buildapi(rout): ...
