# Python Interactive Error Handling and Correction

This repository contains advanced tools for Python error handling and correction, designed to make Python development more efficient and user-friendly.

## Decoher - Interactive Error Handling

Decoher provides interactive error handling capabilities for Python, allowing you to fix runtime errors on the fly without restarting your application.

### Key Features

- ✅ Interactive error correction at runtime
- 🔄 Multiple correction options (fix single line, multiple lines, rewrite functions)
- 📝 Error fix history tracking
- 🛠️ Support for various error types:
  - Syntax errors
  - Indentation errors
  - Name errors
  - Type errors
  - Attribute errors
  - Import errors
  - Index errors
  - Key errors
  - Zero division errors
  - Value errors
- 🔍 Automatic detection and suggestions for whitespace issues
- 🔧 Automatic fix capabilities for common errors
- 📊 PEP 8 style suggestions
- 🔌 Simple enable/disable functionality

### Basic Usage

```python
from qf import decoher

# Enable interactive error handling
decoher.enable()

# Your code with potential errors
# When an error occurs, you'll get an interactive prompt to fix it

# Disable when done
decoher.disable()

# View history of fixes
decoher.show_fix_history()
```

### Interactive Options

When an error is detected, Decoher provides several options:

1. **Apply automatic fix** - For errors that can be automatically fixed
2. **Fix single line** - Edit just the line with the error
3. **Fix multiple lines** - Edit a range of lines
4. **Rewrite entire function** - Replace the whole function containing the error
5. **Choose custom line range** - Select specific lines to edit
6. **Show more context** - View more lines around the error
7. **Continue execution** - Ignore the error and continue
8. **Abort program** - Stop execution
9. **Save a backup** - Create a backup before making changes
10. **Show PEP 8 style suggestions** - Get style recommendations

### Error Detection and Correction

Decoher can detect and help fix various issues:

- **Indentation errors**: Automatically fixes unexpected indentation, missing indentation after colons, and inconsistent indentation levels
- **Syntax errors**: Suggests fixes for missing parentheses, quotes, colons, etc.
- **Whitespace issues**: Detects mixed tabs/spaces, trailing whitespace, and inconsistent indentation
- **Variable errors**: Suggests similar variable names when a name error occurs
- **Type errors**: Provides guidance on argument types and operation compatibility

## Use Cases

- 🔰 Learning Python with reduced frustration
- ⚡ Rapid prototyping and debugging
- 🎬 Live coding demonstrations
- 👨‍🏫 Teaching and mentoring
- 🏛️ Legacy code maintenance

## Limitations

1. Not all errors can be fixed automatically
2. Automatic fixes might not always match programmer intent
3. Performance overhead during development
4. Best used in development and educational contexts, not production

## Best Practices

1. Use during development for quick fixes
2. Disable before deploying to production
3. Use as a learning tool, not a substitute for proper coding practices
4. Combine with proper linting tools for comprehensive code quality
```
