import re

class AmperVariableProcessor:
    def __init__(self):
        # Stores the current value of all &Variables
        # Key: Variable name (e.g., "&QTY"), Value: The current value
        self.amper_vars = {}
        self.var_types = {}  # Stores 'INTEGER', 'REAL', 'CHAR'

    def process_file(self, lines):
        """
        Reads raw lines, executes Amper-logic, and returns 
        pure GPSS code ready for the main simulation parser.
        """
        processed_lines = []
        
        # Regex to identify &Variable usage in a string
        # Matches & followed by alphanumeric characters
        amper_pattern = re.compile(r'&[A-Za-z0-9]+')

        for line in lines:
            line = line.strip()
            
            # Skip empty lines or comments immediately
            if not line or line.startswith('*') or line.startswith(';'):
                processed_lines.append(line)
                continue

            # Tokenize line to check for Preprocessor Directives
            parts = line.split()
            command = parts[0].upper()

            # --- HANDLE DIRECTIVES (Do not pass to Sim) ---
            
            if command in ['INTEGER', 'REAL', 'CHAR']:
                # Declaration: INTEGER &X, &Y
                # We strip commas and handle declarations
                vars_decl = "".join(parts[1:]).split(',')
                for v in vars_decl:
                    v_name = v.strip()
                    self.var_types[v_name] = command
                    # Initialize to default values (0 or empty string)
                    if command == 'CHAR':
                        self.amper_vars[v_name] = ""
                    else:
                        self.amper_vars[v_name] = 0
                continue # Do not output this line to the simulation

            elif command == 'LET':
                # Assignment: LET &I = 10 + 5
                # Remove 'LET' and split by '='
                assignment_body = line[3:].strip()
                if '=' not in assignment_body:
                    print(f"Error: Invalid LET syntax: {line}")
                    continue
                
                target_var, expression = assignment_body.split('=', 1)
                target_var = target_var.strip()
                
                # Evaluate the expression
                # We must substitute any EXISTING &Vars in the expression first!
                expr_subbed = self._substitute_line(expression, amper_pattern)
                
                try:
                    # DANGER: eval is used here for flexibility to match GPSS/H math capabilities.
                    # In a production environment, we would write a safe math parser.
                    # For a personal simulator, this allows full python math support.
                    result = eval(expr_subbed)
                    
                    # Type enforcement
                    v_type = self.var_types.get(target_var, 'REAL') # Default to Real if undeclared
                    if v_type == 'INTEGER':
                        self.amper_vars[target_var] = int(result)
                    elif v_type == 'CHAR':
                        self.amper_vars[target_var] = str(result)
                    else:
                        self.amper_vars[target_var] = float(result)
                        
                except Exception as e:
                    print(f"Error evaluating LET expression '{expression}': {e}")
                
                continue # Do not output this line

            # --- HANDLE STANDARD BLOCKS (Substitute &Vars) ---
            
            # If it's a normal GPSS block (GENERATE, etc.), substitute &Vars
            if '&' in line:
                new_line = self._substitute_line(line, amper_pattern)
                processed_lines.append(new_line)
            else:
                processed_lines.append(line)

        return processed_lines

    def _substitute_line(self, line, pattern):
        """
        Replaces all occurrences of &VAR in a line with their current value.
        """
        # We find all matches
        matches = pattern.findall(line)
        for match in matches:
            if match in self.amper_vars:
                val = str(self.amper_vars[match])
                # Simple string replacement
                # Note: This is simplistic; prevents &VAR2 replacing inside &VAR20
                # A robust version would use regex sub with boundaries.
                line = line.replace(match, val)
            else:
                print(f"Warning: Undefined Amper-Variable {match}")
        return line
