import pytest
import subprocess
import re

pytest.register_assert_rewrite('test_cpu_api')

def compile_program(program_name):
    subprocess.run(["gcc", "-o", program_name, f"{program_name}.c", "-Wall"], check=True)

def cleanup_program(program_name):
    subprocess.run(["rm", "-f", program_name], check=True)

@pytest.fixture(scope="function")
def compiled_program(request):
    program_name = request.param
    compile_program(program_name)
    yield program_name
    cleanup_program(program_name)

def run_program(program_name):
    result = subprocess.run(f"./{program_name}", capture_output=True, text=True, check=True)
    return result.stdout

@pytest.mark.parametrize("compiled_program", ["p1", "p2", "p3", "p4", "p5", "p6", "p7"], indirect=True)
def test_program_output(compiled_program):
    output = run_program(compiled_program)
    
    if compiled_program == "p1":
        assert re.search(r"hello world \(pid:\d+\)", output)
        assert re.search(r"hello, I am child \(pid:\d+\)", output)
        assert re.search(r"hello, I am parent of \d+ \(pid:\d+\)", output)
    
    elif compiled_program == "p2":
        assert re.search(r"hello world \(pid:\d+\)", output)
        assert re.search(r"hello, I am child \(pid:\d+\)", output)
        assert re.search(r"hello, I am parent of \d+ \(wc:\d+\) \(pid:\d+\)", output)
    
    elif compiled_program == "p3":
        assert re.search(r"hello world \(pid:\d+\)", output)
        assert re.search(r"\d+\s+\d+\s+\d+\s+p3\.c", output)  # wc output
        assert re.search(r"hello, I am parent of \d+ \(wc:\d+\) \(pid:\d+\)", output)
        assert "hello, I am child" not in output
        assert "this shouldn't print out" not in output
    
    elif compiled_program == "p4":
        assert output.strip() == ""  # p4 redirects output to a file
        with open("p4.output", "r") as f:
            file_content = f.read()
        assert re.search(r"\d+\s+\d+\s+\d+\s+p4\.c", file_content)  # wc output in file
        cleanup_program("p4.output")
    
    elif compiled_program == "p5":
        assert re.search(r"hello world \(pid:\d+\)", output)
        assert re.search(r"x = 100 \(before fork\)", output)
        assert re.search(r"hello I am child \(pid:\d+\)", output)
        assert re.search(r"x = 100 \(in child\)", output)
        assert re.search(r"x = 200 \(in child after changing\)", output)
        assert re.search(r"hello I am parent of \d+ \(wc:\d+\) \(pid:\d+\)", output)
        assert re.search(r"x = 100 \(in parent\)", output)
        assert re.search(r"x = 300 \(in parent after changing\)", output)
    
    elif compiled_program == "p6":
        assert "File opened with descriptor:" in output
        assert "Child wrote to file" in output
        assert "Parent wrote to file" in output
        
        with open("p6_output.txt", "r") as f:
            file_content = f.read()
        
        assert "Hello from child!" in file_content
        assert "Hello from parent!" in file_content

def test_p4_file_creation():
    compile_program("p4")
    run_program("p4")
    assert subprocess.run(["test", "-f", "p4.output"]).returncode == 0
    cleanup_program("p4")
    cleanup_program("p4.output")

def test_p5_variable_behavior():
    compile_program("p5")
    output = run_program("p5")
    
    # Check that the child's change doesn't affect the parent
    child_value = re.search(r"x = (\d+) \(in child after changing\)", output)
    parent_value = re.search(r"x = (\d+) \(in parent\)", output)
    
    assert child_value and parent_value, "Couldn't find expected output"
    assert int(child_value.group(1)) == 200, "Child didn't change x to 200"
    assert int(parent_value.group(1)) == 100, "Parent's x was affected by child's change"
    
    cleanup_program("p5")

def test_p7_child_first():
    compile_program("p7")
    output = run_program("p7")
    
    lines = output.strip().split('\n')
    assert len(lines) == 2, "Expected exactly two lines of output"
    assert lines[0] == "hello", "First line should be 'hello'"
    assert lines[1] == "goodbye", "Second line should be 'goodbye'"
    
    cleanup_program("p7")

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--capture=no"])