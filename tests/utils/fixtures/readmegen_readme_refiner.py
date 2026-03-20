import json


class DummyLLM:
    """
    A dummy language model class that simulates LLM behavior for testing and development purposes.
    
        Methods:
        - __init__: Initializes the class instance with a response and tracking state.
        - refine_readme: Refines the README content based on the provided sections.
    
        Attributes:
        - called_with: Stores the arguments or state with which the instance was last called.
        - response: The data to be returned or processed by the instance.
    
        The __init__ method sets up the instance with a response, which can be a JSON string or object, and initializes called_with to None for tracking. The refine_readme method processes given README sections, updates called_with with these sections, and returns the refined response. The called_with attribute tracks the last arguments used in method calls, while response holds the data for output or processing.
    """

    def __init__(self, response=None):
        """
        Initialize the class instance with a response and tracking state.
        
        Args:
            response: A JSON string or object representing the response data. If not provided,
                defaults to a JSON string containing placeholder content for badges, introduction, and usage text.
                This default allows the instance to be used immediately without requiring input, simulating a pre-defined response.
        
        Attributes:
            called_with: Stores the arguments or state with which the instance was last called.
                Initialized to None. This is used to track how the instance was invoked, which can be helpful for testing or debugging.
            response: The data to be returned or processed by the instance. It is either the provided response or the default JSON structure.
                The value is stored as a JSON string, ensuring consistency in the data format.
        """
        self.called_with = None
        self.response = response or json.dumps(
            {"badges": "BADGES", "Introduction": "Intro text", "Usage": "Usage text"}
        )

    def refine_readme(self, sections):
        """
        Refines the README content based on the provided sections.
        
        This method is part of a dummy or mock implementation used for testing or simulation.
        It does not perform actual README refinement; instead, it records the input argument
        and returns a predetermined response. This allows the method to be tracked or stubbed
        in tests without executing real refinement logic.
        
        Args:
            sections: The specific sections of the README to be refined or processed.
                This argument is stored internally for later inspection.
        
        Returns:
            The refined README response stored in the instance. This is a fixed response
            attribute (`self.response`) set elsewhere in the instance, not a result of
            processing the input sections.
        
        Attributes:
            called_with: Stores the sections argument passed to the method for tracking
                or state management. This enables verification of method calls in tests.
        """
        self.called_with = sections
        return self.response
