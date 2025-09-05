"""
Docstring Standards and Verification for Federal Reserve ETL Pipeline

Defines and enforces consistent docstring standards across the entire codebase,
following Google-style docstrings with project-specific conventions.
"""

import inspect
import re
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass


@dataclass
class DocstringStandard:
    """
    Standard docstring format for the Federal Reserve ETL Pipeline
    
    This class defines the expected format and content for docstrings
    throughout the project, ensuring consistency and completeness.
    """
    
    # Required sections for different function types
    FUNCTION_SECTIONS = {
        'public_function': ['Args', 'Returns', 'Raises'],
        'private_function': ['Args', 'Returns'],  # Raises optional
        'property': ['Returns'],
        'class_method': ['Args', 'Returns', 'Raises'],
        'static_method': ['Args', 'Returns', 'Raises']
    }
    
    # Required sections for classes
    CLASS_SECTIONS = ['Attributes']  # Optional: Examples, Note
    
    # Common docstring patterns
    PATTERNS = {
        'args_section': re.compile(r'^\s*Args:\s*$', re.MULTILINE),
        'returns_section': re.compile(r'^\s*Returns:\s*$', re.MULTILINE),
        'raises_section': re.compile(r'^\s*Raises:\s*$', re.MULTILINE),
        'attributes_section': re.compile(r'^\s*Attributes:\s*$', re.MULTILINE),
        'examples_section': re.compile(r'^\s*Examples?:\s*$', re.MULTILINE),
        'note_section': re.compile(r'^\s*Notes?:\s*$', re.MULTILINE),
        'parameter': re.compile(r'^\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*(?:\([^)]+\))?\s*:\s*(.+)', re.MULTILINE)
    }


def get_docstring_template(func_type: str, func_name: str) -> str:
    """
    Generate a docstring template for a given function type
    
    Args:
        func_type: Type of function ('public_function', 'private_function', etc.)
        func_name: Name of the function
        
    Returns:
        Formatted docstring template string
        
    Examples:
        >>> template = get_docstring_template('public_function', 'process_data')
        >>> print(template)
        '''
        Brief description of what process_data does
        
        Detailed description explaining the function's purpose,
        behavior, and any important implementation details.
        
        Args:
            param1: Description of first parameter
            param2: Description of second parameter
            
        Returns:
            Description of return value and its type
            
        Raises:
            ExceptionType: Description of when this exception is raised
        '''
    """
    templates = {
        'public_function': '''"""
        Brief description of what {func_name} does
        
        Detailed description explaining the function's purpose,
        behavior, and any important implementation details.
        
        Args:
            param1: Description of first parameter
            param2: Description of second parameter
            
        Returns:
            Description of return value and its type
            
        Raises:
            ExceptionType: Description of when this exception is raised
        """''',
        
        'class': '''"""
        Brief description of what {func_name} class represents
        
        Detailed description explaining the class's purpose,
        responsibilities, and usage patterns.
        
        Attributes:
            attribute1: Description of first attribute
            attribute2: Description of second attribute
            
        Examples:
            >>> instance = {func_name}()
            >>> result = instance.method()
        """''',
        
        'property': '''"""
        Brief description of what this property returns
        
        Returns:
            Description of property value and its type
        """'''
    }
    
    return templates.get(func_type, templates['public_function']).format(func_name=func_name)


def validate_docstring(func: Callable, strict: bool = False) -> Dict[str, Any]:
    """
    Validate a function's docstring against project standards
    
    Checks for required sections, proper formatting, and completeness
    based on the function type and project conventions.
    
    Args:
        func: Function to validate
        strict: Whether to enforce strict validation rules
        
    Returns:
        Dictionary with validation results:
        - is_valid: Whether docstring meets standards
        - missing_sections: List of missing required sections
        - warnings: List of formatting warnings
        - suggestions: List of improvement suggestions
        
    Examples:
        >>> def example_func(x: int) -> str:
        ...     '''Convert integer to string'''
        ...     return str(x)
        >>> result = validate_docstring(example_func)
        >>> print(result['missing_sections'])
        ['Args', 'Returns']
    """
    docstring = inspect.getdoc(func)
    func_name = func.__name__
    
    result = {
        'is_valid': True,
        'missing_sections': [],
        'warnings': [],
        'suggestions': []
    }
    
    if not docstring:
        result['is_valid'] = False
        result['missing_sections'].append('Entire docstring missing')
        return result
    
    # Determine function type
    func_type = _determine_function_type(func)
    required_sections = DocstringStandard.FUNCTION_SECTIONS.get(func_type, [])
    
    # Check for required sections
    for section in required_sections:
        pattern = DocstringStandard.PATTERNS.get(f'{section.lower()}_section')
        if pattern and not pattern.search(docstring):
            result['missing_sections'].append(section)
            result['is_valid'] = False
    
    # Check docstring format and content quality
    _check_docstring_format(docstring, result, strict)
    _check_parameter_documentation(func, docstring, result)
    
    return result


def _determine_function_type(func: Callable) -> str:
    """
    Determine the type of function for docstring validation
    
    Args:
        func: Function to analyze
        
    Returns:
        Function type string ('public_function', 'private_function', etc.)
    """
    func_name = func.__name__
    
    if func_name.startswith('_'):
        return 'private_function'
    elif isinstance(func, property):
        return 'property'
    elif isinstance(func, classmethod):
        return 'class_method'
    elif isinstance(func, staticmethod):
        return 'static_method'
    else:
        return 'public_function'


def _check_docstring_format(docstring: str, result: Dict[str, Any], strict: bool) -> None:
    """
    Check docstring formatting and style
    
    Args:
        docstring: Docstring text to check
        result: Validation result dictionary to update
        strict: Whether to enforce strict formatting rules
    """
    lines = docstring.split('\n')
    
    # Check for brief description (first line)
    if not lines[0].strip():
        result['warnings'].append('First line should contain brief description')
    
    # Check for blank line after brief description
    if len(lines) > 1 and lines[1].strip():
        result['warnings'].append('Brief description should be followed by blank line')
    
    # Check line length (if strict)
    if strict:
        for i, line in enumerate(lines):
            if len(line) > 88:  # Allow some flexibility
                result['warnings'].append(f'Line {i+1} exceeds recommended length')
    
    # Check for proper section formatting
    section_patterns = [
        'Args:', 'Returns:', 'Raises:', 'Attributes:', 
        'Examples:', 'Note:', 'Notes:'
    ]
    
    for line in lines:
        for pattern in section_patterns:
            if pattern in line and not line.strip().endswith(':'):
                result['warnings'].append(f'Section header should end with colon: {pattern}')


def _check_parameter_documentation(func: Callable, docstring: str, result: Dict[str, Any]) -> None:
    """
    Check that all parameters are documented in the docstring
    
    Args:
        func: Function to check
        docstring: Function's docstring
        result: Validation result dictionary to update
    """
    try:
        sig = inspect.signature(func)
        parameters = [name for name, param in sig.parameters.items() 
                     if name not in ('self', 'cls')]
        
        # Extract documented parameters from docstring
        args_match = DocstringStandard.PATTERNS['args_section'].search(docstring)
        if args_match and parameters:
            args_section = docstring[args_match.end():]
            # Find next section or end of docstring
            next_section = None
            for section_name, pattern in DocstringStandard.PATTERNS.items():
                if section_name != 'args_section':
                    match = pattern.search(args_section)
                    if match and (next_section is None or match.start() < next_section):
                        next_section = match.start()
            
            if next_section:
                args_section = args_section[:next_section]
            
            # Find documented parameters
            documented_params = DocstringStandard.PATTERNS['parameter'].findall(args_section)
            documented_names = [param[0] for param in documented_params]
            
            # Check for undocumented parameters
            for param in parameters:
                if param not in documented_names:
                    result['missing_sections'].append(f'Parameter {param} not documented')
                    result['is_valid'] = False
    
    except Exception:
        # If signature inspection fails, skip parameter checking
        pass


def generate_docstring_report(module_name: str) -> Dict[str, Any]:
    """
    Generate a comprehensive docstring compliance report for a module
    
    Args:
        module_name: Name of the module to analyze
        
    Returns:
        Dictionary containing:
        - total_functions: Total number of functions analyzed
        - compliant_functions: Number of functions with valid docstrings
        - compliance_rate: Percentage of compliant functions
        - detailed_results: Per-function validation results
        
    Raises:
        ImportError: If module cannot be imported
    """
    try:
        module = __import__(module_name, fromlist=[''])
    except ImportError as e:
        raise ImportError(f"Cannot import module {module_name}: {str(e)}")
    
    results = {
        'module_name': module_name,
        'total_functions': 0,
        'compliant_functions': 0,
        'compliance_rate': 0.0,
        'detailed_results': {}
    }
    
    # Analyze all functions in the module
    for name in dir(module):
        obj = getattr(module, name)
        if inspect.isfunction(obj) or inspect.ismethod(obj):
            results['total_functions'] += 1
            validation_result = validate_docstring(obj)
            results['detailed_results'][name] = validation_result
            
            if validation_result['is_valid']:
                results['compliant_functions'] += 1
    
    # Calculate compliance rate
    if results['total_functions'] > 0:
        results['compliance_rate'] = (results['compliant_functions'] / results['total_functions']) * 100
    
    return results


# Example of properly formatted docstring following project standards
def example_properly_documented_function(
    variables: List[str],
    start_date: str,
    end_date: Optional[str] = None,
    validate_input: bool = True
) -> Dict[str, Any]:
    """
    Example function demonstrating proper docstring formatting
    
    This function serves as a template for proper docstring formatting
    according to project standards. It includes all required sections
    with clear, descriptive content.
    
    Args:
        variables: List of variable codes to process
        start_date: Start date in YYYY-MM-DD format
        end_date: Optional end date in YYYY-MM-DD format. 
            Defaults to current date if not provided
        validate_input: Whether to validate input parameters before processing
        
    Returns:
        Dictionary containing processing results with keys:
        - success: Boolean indicating if processing succeeded
        - data: Processed data DataFrame
        - metadata: Processing metadata dictionary
        
    Raises:
        ValidationError: If input parameters fail validation
        DataRetrievalError: If data cannot be retrieved from source
        
    Examples:
        >>> result = example_properly_documented_function(
        ...     variables=['FEDFUNDS', 'DGS10'],
        ...     start_date='2020-01-01',
        ...     end_date='2020-12-31'
        ... )
        >>> print(result['success'])
        True
        
    Note:
        This function is for demonstration purposes only and does not
        perform actual data processing.
    """
    return {
        'success': True,
        'data': None,
        'metadata': {
            'variables': variables,
            'start_date': start_date,
            'end_date': end_date
        }
    }