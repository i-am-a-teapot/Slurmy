"""SZS names and mnemonics from https://szs.tptp.org/ (checked 2026-11-16).

Success, NoSuccess, and DataForm are separate vocabularies: SAT/Sat and ASS/Ass
have different meanings. Tables contain names and identifiers, not copied prose.
The 53 Success mappings also match the official SZS_Status.thy (2026-11-18):
https://github.com/TPTPWorld/SZSOntologies/blob/master/SZS_Ontologies/SZS_Status.thy
Conversions use this bundled table offline; they never fetch values at runtime.
"""
from __future__ import annotations
import re
import shlex

REGISTRY_VERSION = '2026-11-16.1'

SUCCESS = {'Success': 'SUC',
 'SemanticSuccess': 'SSU',
 'UnsatisfiabilityPreserving': 'UNP',
 'SatisfiabilityPreserving': 'SAP',
 'TautologyPreserving': 'TAP',
 'EquiSatisfiable': 'ESA',
 'EquiTautologous': 'ETA',
 'ModelExtending': 'MEX',
 'Satisfiable': 'SAT',
 'FinitelySatisfiable': 'FSA',
 'FiniteTheorem': 'FTH',
 'Theorem': 'THM',
 'SatisfiableAxiomsTheorem': 'STH',
 'Equivalent': 'EQV',
 'TautologousConclusion': 'TAC',
 'WeakerConclusion': 'WEC',
 'EquivalentTheorem': 'ETH',
 'Tautology': 'TAU',
 'WeakerTautologousConclusion': 'WTC',
 'WeakerTheorem': 'WTH',
 'FiniteTautology': 'FTT',
 'CounterUnsatisfiabilityPreserving': 'CUP',
 'CounterSatisfiabilityPreserving': 'CSP',
 'CounterTautologyPreserving': 'CTP',
 'EquiCounterSatisfiable': 'ECS',
 'EquiCounterTautologous': 'ECA',
 'CounterModelExtending': 'CMX',
 'CounterSatisfiable': 'CSA',
 'FinitelyCounterSatisfiable': 'FCS',
 'FiniteCounterTheorem': 'FCT',
 'CounterTheorem': 'CTH',
 'SatisfiableAxiomsCounterTheorem': 'SCT',
 'CounterEquivalent': 'CEQ',
 'UnsatisfiableConclusion': 'UNC',
 'WeakerCounterConclusion': 'WCC',
 'EquivalentCounterTheorem': 'ECT',
 'Unsatisfiable': 'UNS',
 'WeakerUnsatisfiableConclusion': 'WUC',
 'WeakerCounterTheorem': 'WCT',
 'FinitelyUnsatisfiable': 'FUN',
 'ContradictoryAxioms': 'CAX',
 'SatisfiableConclusionContradictoryAxioms': 'SCA',
 'SatisfiableCounterConclusionContradictoryAxioms': 'SCC',
 'TautologousConclusionContradictoryAxioms': 'TCA',
 'WeakerConclusionContradictoryAxioms': 'WCA',
 'UnsatisfiableConclusionContradictoryAxioms': 'UCA',
 'NoConsequence': 'NOC',
 'TypeCheckSuccess': 'TSU',
 'TypeCheckPartial': 'TCP',
 'TypeCheckedComplete': 'TCC',
 'VerifySuccess': 'VSU',
 'VerifiedGood': 'VSG',
 'VerifiedBad': 'VSB'}

NO_SUCCESS = {'NoSuccess': 'NOS',
 'Unknown': 'UNK',
 'Stopped': 'STP',
 'InProgress': 'INP',
 'NotTried': 'NTT',
 'NotTriedYet': 'NTY',
 'Error': 'ERR',
 'Forced': 'FOR',
 'GaveUp': 'GUP',
 'OSError': 'OSE',
 'InputError': 'INE',
 'SyntaxError': 'SYE',
 'SemanticError': 'SEE',
 'TypeError': 'TYE',
 'Unsemantic': 'USM',
 'UsageError': 'USE',
 'User': 'USR',
 'ResourceOut': 'RSO',
 'Timeout': 'TMO',
 'CPUTimeout': 'CTO',
 'WCTimeout': 'WTO',
 'MemoryOut': 'MMO',
 'Incomplete': 'INC',
 'Inappropriate': 'IAP',
 'Incorrect': 'ICT',
 'Assumed': 'ASS',
 'Open': 'OPN',
 'NotVerified': 'NVE',
 'FailedVerified': 'FVE'}

DATA_FORMS = {'Data': 'Dat',
 'LogicalData': 'LDa',
 'Solution': 'Sln',
 'Proof': 'Prf',
 'Interpretation': 'Int',
 'ListOfFormulae': 'Lof',
 'Derivation': 'Der',
 'Refutation': 'Ref',
 'CNFRefutation': 'CRf',
 'Model': 'Mod',
 'DomainInterpretation': 'DIn',
 'FiniteInterpretation': 'FIn',
 'InfiniteInterpretation': 'IIn',
 'DomainModel': 'DMo',
 'FiniteModel': 'FMo',
 'InfiniteModel': 'IMo',
 'HerbrandInterpretation': 'HIn',
 'HerbrandModel': 'HMo',
 'FormulaHerbrandInterpretation': 'FHi',
 'FormulaHerbrandModel': 'FHm',
 'SaturationHerbrandInterpretation': 'SHi',
 'SaturationHerbrandModel': 'Sat',
 'NotASolution': 'NSo',
 'Assurance': 'Ass',
 'IncompleteProof': 'IPr',
 'IncompleteInterpretation': 'InI',
 'NonLogicalData': 'NLd',
 'Comment': 'Com',
 'FreeText': 'FTx',
 'Verification': 'Ver',
 'None': 'Non'}

STATUSES = {**SUCCESS, **NO_SUCCESS}
_STATUS_NAMES = {alias.casefold(): name for name,code in STATUSES.items() for alias in (name,code)}
_STATUS_NAMES['typecheckcomplete'] = 'TypeCheckedComplete'
_FORM_NAMES = {alias.casefold(): name for name,code in DATA_FORMS.items() for alias in (name,code)}
_FORM_NAMES.update(saturation='SaturationHerbrandModel', definitions='Assurance')
ASSUMED_RE = re.compile(r'^(?:Assumed|ASS)\(\s*([A-Za-z]+)\s*,\s*([A-Za-z]+)\s*\)$', re.I)
STATUS_PATTERN = r'[A-Za-z][A-Za-z0-9_-]*(?:\(\s*[A-Za-z]+\s*,\s*[A-Za-z]+\s*\))?'
STATUS_RE = re.compile(r'\bSZS\s+status\s+('+STATUS_PATTERN+r')', re.I)
TIMEOUTS = {'Timeout','CPUTimeout','WCTimeout'}
ERRORS = {'Error','OSError','InputError','SyntaxError','SemanticError','TypeError','Unsemantic',
          'UsageError','Incorrect','FailedVerified'}


def canonical(value):
    value = str(value or '').strip()
    compound = ASSUMED_RE.fullmatch(value)
    if compound:
        reason, assumption = map(canonical, compound.groups())
        if reason in NO_SUCCESS and reason != 'Assumed' and assumption in SUCCESS:
            return f'Assumed({reason},{assumption})'
    return _STATUS_NAMES.get(value.casefold(), value)


def base(value):
    return canonical(value).split('(',1)[0]


def mnemonic(value):
    value = canonical(value)
    compound = ASSUMED_RE.fullmatch(value)
    if compound:
        reason, assumption = map(canonical, compound.groups())
        if reason in NO_SUCCESS and reason != 'Assumed' and assumption in SUCCESS:
            return 'ASS('+mnemonic(reason)+','+mnemonic(assumption)+')'
        return ''
    return STATUSES.get(value, '')


def ontology(value):
    name = base(value)
    return 'Success' if name in SUCCESS else 'NoSuccess' if name in NO_SUCCESS else ''


def successful(value):
    return ontology(value) == 'Success'


def data_form(value):
    value = str(value or '').strip()
    return _FORM_NAMES.get(value.casefold(), value)


def data_mnemonic(value):
    return DATA_FORMS.get(data_form(value), '')


def execution_status(value):
    name = base(value)
    if name in TIMEOUTS: return 'time-limit'
    if name == 'MemoryOut': return 'memory-limit'
    if name == 'ResourceOut': return 'resource-limit'
    if name in ERRORS: return 'solver-error'
    if name == 'CounterSatisfiable': return 'counter-satisfiable'
    if name in SUCCESS: return 'ok'
    if name in NO_SUCCESS: return 'no-success'
    return ''


def normalize_execution(current, value, return_code=''):
    if current in {'time-limit','memory-limit','resource-limiter-error','worker-error','interrupted'}:
        return current
    target = execution_status(value)
    if current == 'solver-error' and str(return_code).isdigit() and int(return_code) >= 128 and target in {'ok','counter-satisfiable','no-success'}:
        return current
    return target or current


def normalize_row(row):
    row = dict(row)
    row['szs_status'] = canonical(row.get('szs_status'))
    row['szs_output'] = data_form(row.get('szs_output'))
    row['status'] = normalize_execution(row.get('status',''), row['szs_status'], row.get('return_code',''))
    if base(row['szs_status']) in TIMEOUTS: row['timed_out'] = 'true'
    if base(row['szs_status']) == 'MemoryOut': row['memory_out'] = 'true'
    return row


def shell_library():
    lines = ['# Generated from implementation/szs.py; requires Bash 4+.', 'szs_status_name() {',
             '  local value=$1 reason answer', '  local compact=${value//[[:space:]]/}',
             '  if [[ ${compact,,} =~ ^(assumed|ass)\\(([a-z]+),([a-z]+)\\)$ ]]; then',
             '    reason=$(szs_status_name "${BASH_REMATCH[2]}")',
             '    answer=$(szs_status_name "${BASH_REMATCH[3]}")',
             '    case $reason in '+ '|'.join(name for name in NO_SUCCESS if name!='Assumed') + ') ;; *) printf "%s\\n" "$value"; return ;; esac',
             '    case $answer in '+ '|'.join(SUCCESS) + ') ;; *) printf "%s\\n" "$value"; return ;; esac',
             '    printf "Assumed(%s,%s)\\n" "$reason" "$answer"; return', '  fi', '  case ${value,,} in']
    for alias,name in _STATUS_NAMES.items(): lines.append(f'    {alias}) printf "%s\\n" {shlex.quote(name)} ;;')
    lines += ['    *) printf "%s\\n" "$value" ;;', '  esac', '}', 'szs_data_name() {', '  case ${1,,} in']
    for alias,name in _FORM_NAMES.items(): lines.append(f'    {alias}) printf "%s\\n" {shlex.quote(name)} ;;')
    lines += ['    *) printf "%s\\n" "$1" ;;', '  esac', '}', 'szs_execution() {',
              '  local name=$(szs_status_name "$1")', '  name=${name%%(*}', '  case $name in']
    for name in STATUSES: lines.append(f'    {name}) printf "%s\\n" {shlex.quote(execution_status(name))} ;;')
    lines += ['    *) printf "\\n" ;;', '  esac', '}']
    return '\n'.join(lines)+'\n'


def awk_library():
    # Enum-only lookup stays cheap for the overwhelmingly common plain statuses.
    statements=[]
    for alias,name in _STATUS_NAMES.items():
        statements += [f'SZS_NAME["{alias}"]="{name}"',f'SZS_EXEC["{name}"]="{execution_status(name)}"',f'SZS_ONTOLOGY["{name}"]="{ontology(name)}"']
    return '''BEGIN {'''+ ';'.join(statements)+'''}
function szs_canonical(value, compact, fields, n) {
    compact=tolower(value)
    if (index(compact,"(")) {
        gsub(/[[:space:]]/,"",compact)
        if (compact ~ /^(assumed|ass)\\([a-z]+,[a-z]+\\)$/) {
            sub(/^(assumed|ass)\\(/,"",compact); sub(/\\)$/, "",compact)
            split(compact,fields,",")
            if (SZS_ONTOLOGY[SZS_NAME[fields[1]]]=="NoSuccess" && SZS_NAME[fields[1]]!="Assumed" && SZS_ONTOLOGY[SZS_NAME[fields[2]]]=="Success")
                return "Assumed(" SZS_NAME[fields[1]] "," SZS_NAME[fields[2]] ")"
        }
    }
    return compact in SZS_NAME ? SZS_NAME[compact] : value
}
function szs_normalize(current, value, code, name, target) {
    if (current ~ /^(time-limit|memory-limit|resource-limiter-error|worker-error|interrupted)$/) return current
    name=szs_canonical(value); sub(/\\(.*/,"",name); target=SZS_EXEC[name]
    if (current=="solver-error" && code+0>=128 && target ~ /^(ok|counter-satisfiable|no-success)$/) return current
    return target!="" ? target : current
}
function protect_csv(line, quoted, output, i, char) {
    for (i=1;i<=length(line);i++) {
        char=substr(line,i,1)
        if (char=="\\\"") quoted=!quoted
        output=output (char=="," && quoted ? "\\034" : char)
    }
    return output
}
'''


def remote_program(source):
    """Bundle this module for a remote Python process reading its program on stdin."""
    from pathlib import Path
    registry = Path(__file__).read_text()
    return ('import sys,types\n_szs=types.ModuleType("szs")\nsys.modules["szs"]=_szs\n'
            +f'exec(compile({registry!r},"szs.py","exec"),_szs.__dict__)\n'
            +f'exec(compile({source!r},"remote_export.py","exec"))\n').encode()
