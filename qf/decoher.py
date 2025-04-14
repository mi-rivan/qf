import inspect
import sys
import traceback
import re
import ast
import os

# Global state
_enabled = False
_history = []  # Store history of fixes

def enable():
    """Enable interactive error handling for the entire program."""
    global _enabled
    _enabled = True
    # Install the exception hook
    sys.excepthook = _interactive_exception_handler
    print("Interactive error handling enabled")

def disable():
    """Disable interactive error handling."""
    global _enabled
    _enabled = False
    # Restore the default exception hook
    sys.excepthook = sys.__excepthook__
    print("Interactive error handling disabled")

def _get_function_bounds(lines, line_index):
    """Find the start and end line numbers of the function containing the error."""
    # Find function start (look for def or class)
    func_start = line_index
    while func_start >= 0:
        if re.match(r'^\s*(def|class)\s+\w+', lines[func_start]):
            break
        func_start -= 1
    
    if func_start < 0:
        func_start = 0  # Not in a function, start from the beginning
    
    # Find function end (look for next def/class at same or lower indentation)
    start_indent = len(lines[func_start]) - len(lines[func_start].lstrip())
    func_end = line_index
    while func_end < len(lines) - 1:
        func_end += 1
        # If we find a line with same or less indentation that's a def/class, we've found the end
        line = lines[func_end]
        if line.strip() and len(line) - len(line.lstrip()) <= start_indent:
            if re.match(r'^\s*(def|class)\s+\w+', line):
                func_end -= 1
                break
    
    return func_start, func_end

def _save_fix_history(filename, original_lines, new_lines, fix_type):
    """Save the fix to history."""
    global _history
    _history.append({
        'timestamp': import_time(),
        'filename': filename,
        'original': original_lines,
        'fixed': new_lines,
        'type': fix_type
    })
    
    # Limit history size
    if len(_history) > 20:
        _history.pop(0)

def import_time():
    """Import time module and return current time."""
    import datetime
    return datetime.datetime.now()

def _suggest_similar_names(var_name, lines):
    """Suggest similar variable names that might exist in the code."""
    # Extract all potential variable names from the code
    all_names = set()
    for line in lines:
        # Simple extraction of words that could be variable names
        words = re.findall(r'\b[a-zA-Z_][a-zA-Z0-9_]*\b', line)
        all_names.update(words)
    
    # Find similar names using Levenshtein distance
    similar_names = []
    for name in all_names:
        # Skip keywords, built-ins, and very short names
        if name in ['if', 'else', 'for', 'while', 'def', 'class', 'return', 'True', 'False', 'None'] or len(name) < 2:
            continue
        
        # Calculate similarity (simple version)
        distance = _levenshtein_distance(var_name, name)
        if distance <= 2 and distance > 0:  # Close but not identical
            similar_names.append(name)
    
    if similar_names:
        print("Did you mean one of these? " + ", ".join(similar_names))

def _levenshtein_distance(s1, s2):
    """Calculate the Levenshtein distance between two strings."""
    if len(s1) < len(s2):
        return _levenshtein_distance(s2, s1)
    
    if len(s2) == 0:
        return len(s1)
    
    previous_row = range(len(s2) + 1)
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row
    
    return previous_row[-1]

def _auto_fix_indentation(lines, error_line_index, error_message):
    """Attempt to automatically fix indentation errors."""
    fixed_lines = lines.copy()
    line = fixed_lines[error_line_index]
    
    if "unexpected indent" in error_message:
        # Remove leading whitespace
        fixed_lines[error_line_index] = line.lstrip()
        return fixed_lines
    
    elif "expected an indented block" in error_message:
        # Add standard 4-space indentation
        fixed_lines[error_line_index] = "    " + line.lstrip()
        return fixed_lines
    
    elif "unindent does not match" in error_message:
        # Try to match indentation with previous non-empty line
        prev_index = error_line_index - 1
        while prev_index >= 0 and not fixed_lines[prev_index].strip():
            prev_index -= 1
        
        if prev_index >= 0:
            prev_indent = len(fixed_lines[prev_index]) - len(fixed_lines[prev_index].lstrip())
            fixed_lines[error_line_index] = " " * prev_indent + line.lstrip()
        
        return fixed_lines
    
    return None  # No automatic fix available

def _detect_whitespace_errors(lines, line_index):
    """Detect and suggest fixes for common whitespace errors."""
    line = lines[line_index]
    fixes = []
    
    # Check for mixed tabs and spaces
    if '\t' in line and ' ' in line:
        fixes.append({
            'type': 'mixed_indentation',
            'message': 'Mixed tabs and spaces detected',
            'fix': line.replace('\t', '    ')
        })
    
    # Check for trailing whitespace
    if line.rstrip() != line and line.strip():
        fixes.append({
            'type': 'trailing_whitespace',
            'message': 'Trailing whitespace detected',
            'fix': line.rstrip()
        })
    
    # Check for inconsistent indentation (not divisible by 4)
    indent = len(line) - len(line.lstrip())
    if indent % 4 != 0 and indent > 0:
        new_indent = (indent // 4) * 4  # Round down to nearest multiple of 4
        fixes.append({
            'type': 'inconsistent_indent',
            'message': f'Indentation not divisible by 4 (current: {indent} spaces)',
            'fix': ' ' * new_indent + line.lstrip()
        })
    
    return fixes

def _auto_fix_syntax_errors(lines, line_index, error_message):
    """Attempt to automatically fix common syntax errors."""
    line = lines[line_index]
    fixed_lines = lines.copy()
    
    # Missing closing parenthesis
    if "unexpected EOF" in error_message and "(" in line and ")" not in line:
        fixed_lines[line_index] = line + ")"
        return fixed_lines
    
    # Missing closing quote
    if "EOL while scanning string literal" in error_message:
        if "'" in line and line.count("'") % 2 != 0:
            fixed_lines[line_index] = line + "'"
            return fixed_lines
        elif '"' in line and line.count('"') % 2 != 0:
            fixed_lines[line_index] = line + '"'
            return fixed_lines
    
    # Missing colon after if/for/while/def
    if "expected ':'" in error_message:
        for keyword in ['if', 'for', 'while', 'def', 'class', 'else', 'elif', 'except', 'finally']:
            if re.search(rf'\b{keyword}\b.*\S$', line):
                fixed_lines[line_index] = line + ":"
                return fixed_lines
    
    return None

def _interactive_exception_handler(exc_type, exc_value, exc_traceback):
    """Custom exception handler that provides interactive error correction."""
    if not _enabled:
        # If disabled, use the default exception handler
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return
    
    # Get the traceback information
    tb = traceback.extract_tb(exc_traceback)
    
    # Find the frame where the error occurred
    frame_info = None
    for frame in tb:
        # Skip frames from this module
        if frame.filename != __file__:
            frame_info = frame
            break
    
    if frame_info:
        try:
            # Try to get the source code of the file
            with open(frame_info.filename, 'r') as f:
                lines = f.readlines()
            
            # Remove trailing newlines
            lines = [line.rstrip('\n') for line in lines]
            
            # Display error information
            print("\n" + "="*60)
            print(f"Error: {exc_type.__name__}: {exc_value}")
            print(f"File: {frame_info.filename}")
            
            # Get the actual line number from traceback and ensure it's valid
            actual_lineno = 1  # Default to line 1
            try:
                # Handle different traceback formats
                if hasattr(frame_info, 'lineno'):
                    actual_lineno = frame_info.lineno
                elif isinstance(frame_info, tuple) and len(frame_info) >= 2:
                    # For older Python versions that use tuples
                    actual_lineno = frame_info[1]
                
                # Ensure it's an integer - handle various types safely
                if actual_lineno is None:
                    actual_lineno = 1
                elif not isinstance(actual_lineno, int):
                    try:
                        actual_lineno = int(actual_lineno)
                    except (ValueError, TypeError):
                        actual_lineno = 1
            except Exception:
                # If anything goes wrong, use line 1
                actual_lineno = 1
            
            # Convert to zero-based index for our lines list with safety checks
            line_index = 0  # Default to first line
            if lines:  # Make sure we have lines
                line_index = max(0, actual_lineno - 1)  # Ensure non-negative
                line_index = min(line_index, len(lines) - 1)  # Ensure not beyond end of file
                
            print(f"Line {actual_lineno}: {lines[line_index]}")
            print("="*60)
            
            # Show context (a few lines before and after)
            context_start = max(0, line_index - 2)
            context_end = min(len(lines), line_index + 3)
            
            for i in range(context_start, context_end):
                prefix = "→ " if i == line_index else "  "
                print(f"{prefix}{i+1}: {lines[i]}")
            
            # Enhanced error suggestions based on error type
            error_type_name = exc_type.__name__
            error_message = str(exc_value)
            
            # Check for various auto-fix possibilities
            auto_fixed_lines = None
            auto_fix_type = None
            
            # Check for indentation errors
            if "IndentationError" in error_type_name:
                auto_fixed_lines = _auto_fix_indentation(lines, line_index, error_message)
                auto_fix_type = "indentation"
            
            # Check for syntax errors
            elif "SyntaxError" in error_type_name:
                auto_fixed_lines = _auto_fix_syntax_errors(lines, line_index, error_message)
                auto_fix_type = "syntax"
            
            # Check for whitespace issues (even if not causing errors)
            whitespace_fixes = _detect_whitespace_errors(lines, line_index)
            if whitespace_fixes and not auto_fixed_lines:
                # Apply the first whitespace fix
                auto_fixed_lines = lines.copy()
                auto_fixed_lines[line_index] = whitespace_fixes[0]['fix']
                auto_fix_type = "whitespace"
            
            # Display auto-fix if available
            if auto_fixed_lines:
                print(f"\nAuto-fix available for {auto_fix_type} error!")
                print("Suggested fix:")
                for i in range(context_start, context_end):
                    prefix = "→ " if i == line_index else "  "
                    if i == line_index:
                        print(f"{prefix}{i+1}: {auto_fixed_lines[i]} (FIXED)")
                    else:
                        print(f"{prefix}{i+1}: {auto_fixed_lines[i]}")
                
                # For whitespace issues, show detailed explanation
                if auto_fix_type == "whitespace" and whitespace_fixes:
                    print(f"\nWhitespace issue: {whitespace_fixes[0]['message']}")
            
            # Show detailed error suggestions
            if "SyntaxError" in error_type_name:
                print("\nPossible fix: Check for missing parentheses, quotes, or colons")
                if "invalid syntax" in error_message:
                    print("Common causes: mismatched brackets, missing commas, or invalid operators")
                elif "EOL while scanning string literal" in error_message:
                    print("Missing closing quote - add a matching quote character")
                elif "unexpected EOF" in error_message:
                    print("Missing closing bracket or parenthesis")
                elif "expected ':'" in error_message:
                    print("Add a colon at the end of the line")
            
            # Ask user for correction approach
            print("\nAdvanced Error Correction Options:")
            if auto_fixed_lines:
                print("  0. Apply automatic fix (recommended)")
            print("  1. Fix single line")
            print("  2. Fix multiple lines")
            print("  3. Rewrite entire function")
            print("  4. Choose custom line range to fix")
            print("  5. Show more context")
            print("  6. Continue execution (ignore error)")
            print("  7. Abort program")
            print("  8. Save a backup before fixing")
            print("  9. Show PEP 8 style suggestions")
            
            choice = input("Choose an option (0-9): ")
            
            if choice == '0' and auto_fixed_lines:
                # Apply automatic fix
                with open(frame_info.filename, 'w') as f:
                    f.write('\n'.join(auto_fixed_lines) + '\n')
                
                _save_fix_history(frame_info.filename, [lines[line_index]], [auto_fixed_lines[line_index]], f"auto_fix_{auto_fix_type}")
                print(f"File updated with automatic fix. Please run your program again.")
                sys.exit(0)
            
            elif choice == '9':
                # Show PEP 8 style suggestions
                print("\nPEP 8 Style Suggestions:")
                
                # Check line length
                if len(lines[line_index]) > 79:
                    print(f"- Line too long ({len(lines[line_index])} > 79 characters)")
                
                # Check variable naming
                var_names = re.findall(r'\b[a-zA-Z_][a-zA-Z0-9_]*\b', lines[line_index])
                for var in var_names:
                    if re.match(r'^[A-Z][a-z]', var) and not re.match(r'^[A-Z]+$', var):
                        print(f"- Variable '{var}' uses CamelCase instead of snake_case")
                
                # Check whitespace around operators
                if re.search(r'[^\s][+\-*/=][^\s]', lines[line_index]):
                    print("- Missing spaces around operators")
                
                # Check imports
                if line_index < 20 and "import" in lines[line_index]:
                    if "import *" in lines[line_index]:
                        print("- Wildcard imports (import *) are discouraged")
                
                # Recursively call the handler to get back to the options
                _interactive_exception_handler(exc_type, exc_value, exc_traceback)
                return
            
            elif choice == '1':  # Fixed: Changed from unindented to properly indented
                # Single line fix
                print(f"\nCurrent line {actual_lineno}: {lines[line_index]}")
                print("Enter the corrected line:")
                new_line = input("> ")
                
                # Update the file with the correction
                original_line = lines[line_index]
                lines[line_index] = new_line
                with open(frame_info.filename, 'w') as f:
                    f.write('\n'.join(lines) + '\n')
                
                _save_fix_history(frame_info.filename, [original_line], [new_line], "single_line")
                print(f"File updated. Please run your program again.")
            
            elif choice == '2':  # Fixed: Changed from unindented to properly indented
                # Multi-line fix
                print("\nEnter the starting line number:")
                try:
                    start_line = int(input("> ")) - 1  # Convert to 0-based index
                    start_line = max(0, min(start_line, len(lines) - 1))
                    
                    print("Enter the ending line number:")
                    end_line = int(input("> ")) - 1  # Convert to 0-based index
                    end_line = max(start_line, min(end_line, len(lines) - 1))
                    
                    print("\nCurrent lines:")
                    for i in range(start_line, end_line + 1):
                        print(f"{i+1}: {lines[i]}")
                    
                    print("\nEnter the corrected lines (type 'END' on a new line when finished):")
                    new_lines = []
                    while True:
                        line = input()
                        if line == 'END':
                            break
                        new_lines.append(line)
                    
                    # Update the file with the correction
                    original_lines = lines[start_line:end_line+1]
                    lines[start_line:end_line+1] = new_lines
                    with open(frame_info.filename, 'w') as f:
                        f.write('\n'.join(lines) + '\n')
                    
                    _save_fix_history(frame_info.filename, original_lines, new_lines, "multi_line")
                    print(f"File updated. Please run your program again.")
                    
                except ValueError:
                    print("Invalid line number. Aborting.")
            
            elif choice == '3':
                # Rewrite entire function
                func_start, func_end = _get_function_bounds(lines, line_index)
                
                print("\nCurrent function:")
                for i in range(func_start, func_end + 1):
                    print(f"{i+1}: {lines[i]}")
                
                print("\nEnter the rewritten function (type 'END' on a new line when finished):")
                new_func_lines = []
                while True:
                    line = input()
                    if line == 'END':
                        break
                    new_func_lines.append(line)
                
                # Update the file with the correction
                original_func = lines[func_start:func_end+1]
                lines[func_start:func_end+1] = new_func_lines
                with open(frame_info.filename, 'w') as f:
                    f.write('\n'.join(lines) + '\n')
                
                _save_fix_history(frame_info.filename, original_func, new_func_lines, "function_rewrite")
                print(f"Function rewritten. Please run your program again.")
            
            elif choice == '4':
                # Custom line range
                print("\nEnter the starting line number:")
                try:
                    start_line = int(input("> ")) - 1  # Convert to 0-based index
                    start_line = max(0, min(start_line, len(lines) - 1))
                    
                    print("Enter the ending line number:")
                    end_line = int(input("> ")) - 1  # Convert to 0-based index
                    end_line = max(start_line, min(end_line, len(lines) - 1))
                    
                    print("\nCurrent lines:")
                    for i in range(start_line, end_line + 1):
                        print(f"{i+1}: {lines[i]}")
                    
                    print("\nEnter the corrected lines (type 'END' on a new line when finished):")
                    new_lines = []
                    while True:
                        line = input()
                        if line == 'END':
                            break
                        new_lines.append(line)
                    
                    # Update the file with the correction
                    original_lines = lines[start_line:end_line+1]
                    lines[start_line:end_line+1] = new_lines
                    with open(frame_info.filename, 'w') as f:
                        f.write('\n'.join(lines) + '\n')
                    
                    _save_fix_history(frame_info.filename, original_lines, new_lines, "custom_range")
                    print(f"File updated. Please run your program again.")
                    
                except ValueError:
                    print("Invalid line number. Aborting.")
                    
            elif choice == '5':
                # Show more context
                print("\nEnter the number of lines to show before and after the error:")
                try:
                    context_lines = int(input("> "))
                    context_lines = max(1, min(context_lines, 50))  # Reasonable limits
                    
                    context_start = max(0, line_index - context_lines)
                    context_end = min(len(lines), line_index + context_lines + 1)
                    
                    print("\nExtended context:")
                    for i in range(context_start, context_end):
                        prefix = "→ " if i == line_index else "  "
                        print(f"{prefix}{i+1}: {lines[i]}")
                    
                    # Recursively call the handler to get back to the options
                    _interactive_exception_handler(exc_type, exc_value, exc_traceback)
                    return
                    
                except ValueError:
                    print("Invalid number. Showing default context.")
                    _interactive_exception_handler(exc_type, exc_value, exc_traceback)
                    return
                    
            elif choice == '6':
                print("Continuing execution (error ignored)...")
                return
                
            elif choice == '7':
                print("Execution aborted.")
                sys.exit(1)
                
            elif choice == '8':
                # Create backup
                backup_path = frame_info.filename + ".backup." + str(import_time().strftime("%Y%m%d_%H%M%S"))
                with open(backup_path, 'w') as f:
                    f.write('\n'.join(lines) + '\n')
                print(f"Backup created at: {backup_path}")
                
                # Recursively call the handler to get back to the options
                _interactive_exception_handler(exc_type, exc_value, exc_traceback)
                return
                
            else:
                print("Invalid choice. Aborting.")
                sys.exit(1)
            
        except Exception as e:
            print(f"Error in interactive handler: {e}")
            # Fall back to the default exception handler
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
    else:
        # If we can't determine the file/line, use the default handler
        sys.__excepthook__(exc_type, exc_value, exc_traceback)

def show_fix_history():
    """Display the history of fixes made."""
    global _history
    if not _history:
        print("No fix history available.")
        return
    
    print("\nFix History:")
    for i, fix in enumerate(_history):
        print(f"{i+1}. [{fix['timestamp']}] {fix['filename']} - {fix['type']}")
    
    print("\nEnter a number to see details (or 0 to exit):")
    try:
        choice = int(input("> "))
        if choice == 0 or choice > len(_history):
            return
        
        fix = _history[choice-1]
        print(f"\nFix #{choice} Details:")
        print(f"Timestamp: {fix['timestamp']}")
        print(f"File: {fix['filename']}")
        print(f"Type: {fix['type']}")
        
        print("\nOriginal:")
        for line in fix['original']:
            print(f"  {line}")
        
        print("\nFixed:")
        for line in fix['fixed']:
            print(f"  {line}")
            
    except ValueError:
        print("Invalid choice.")

# Example usage
if __name__ == "__main__":
    print("Example usage:")
    print("  import decoher")
    print("  decoher.enable()")
    print("  # Your code here")
    print("  decoher.disable()")
    print("  # To view fix history:")
    print("  decoher.show_fix_history()")
    