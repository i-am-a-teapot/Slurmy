"""Literal environment syntax and safe shell emission."""
import subprocess
import unittest
from solver_environment import parse, exports


class SolverEnvironmentTests(unittest.TestCase):
    def test_assignments_quotes_whitespace_and_empty_values(self):
        self.assertEqual(parse('X=Y Z=3\nHello = World\nEMPTY= NEXT = "hello world"\nEQ="a=b"'),
                         dict(X='Y',Z='3',Hello='World',EMPTY='',NEXT='hello world',EQ='a=b'))
        self.assertEqual(parse("A='one two' B=three\\ four C= D=''"),dict(A='one two',B='three four',C='',D=''))
        self.assertEqual(parse(' \n\t'),{})

    def test_invalid_names_duplicates_quotes_and_control_characters(self):
        for text in ['1A=x','A-B=x','A x','A=x A=y','A="x',"A='x",'A=x\\','A=\x00','A=x\nmissing']:
            with self.subTest(text=text),self.assertRaises(ValueError):parse(text)

    def test_values_remain_literal_when_exported(self):
        values=parse('A="$(echo unsafe); `echo unsafe` $HOME" B="a b"')
        result=subprocess.run(['bash','-c',exports(values)+'printf "%s\\n" "$A" "$B"'],capture_output=True,text=True,check=True)
        self.assertEqual(result.stdout.splitlines(),[values['A'],values['B']])
