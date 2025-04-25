#!/usr/bin/env python3
"""
A sample file for testing the documentation review functionality.
"""

def calculate_sum(a, b):
    return a + b

class DataProcessor:
    def __init__(self, data):
        self.data = data
    
    def process(self):
        # Process the data
        result = []
        for item in self.data:
            result.append(item * 2)
        return result

def main():
    # Test the DataProcessor
    processor = DataProcessor([1, 2, 3, 4, 5])
    processed_data = processor.process()
    print(f"Processed data: {processed_data}")
    
    # Test calculate_sum
    total = calculate_sum(10, 20)
    print(f"Sum: {total}")

if __name__ == "__main__":
    main()
