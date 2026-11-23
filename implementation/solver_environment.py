"""Parse literal NAME=value assignments; never evaluate shell expressions."""
import re
import shlex

NAME = re.compile(r'[A-Za-z_][A-Za-z0-9_]*')


def parse(value):
    if value is None:return {}
    if not isinstance(value,str):raise ValueError('Environment variables must be text.')
    if any(ord(char)<32 and char not in '\r\n\t' or ord(char)==127 for char in value):
        raise ValueError('Environment variables cannot contain control characters.')
    result={};position=0;length=len(value)
    while position<length:
        while position<length and value[position].isspace():position+=1
        if position==length:break
        match=NAME.match(value,position)
        if not match:raise ValueError('Use environment variable names containing letters, digits and underscores, starting with a letter or underscore.')
        name=match.group();position=match.end()
        while position<length and value[position] in ' \t':position+=1
        if position==length or value[position]!='=':raise ValueError(f'Expected = after environment variable {name}.')
        if name in result:raise ValueError(f'Environment variable {name} is assigned more than once.')
        position+=1
        # Whitespace around = is allowed. A following assignment starts a new
        # variable; use quotes to include spaces or assignment-like text in a value.
        after=position
        while after<length and value[after] in ' \t':after+=1
        if after>position and re.match(r'[A-Za-z_][A-Za-z0-9_]*[ \t]*=',value[after:]):
            result[name]='';position=after;continue
        position=after;chars=[];quote=None
        while position<length:
            char=value[position]
            if quote is None and char.isspace():break
            if char==quote:
                quote=None;position+=1;continue
            if quote is None and char in "\"'":
                quote=char;position+=1;continue
            if char=='\\' and quote!="'":
                position+=1
                if position==length:raise ValueError(f'Incomplete escape in environment variable {name}.')
                char=value[position]
            chars.append(char);position+=1
        if quote:raise ValueError(f'Unclosed quote in environment variable {name}.')
        result[name]=''.join(chars)
    return result


def exports(values):
    return ''.join(f'export {name}={shlex.quote(value)}\n' for name,value in values.items())
