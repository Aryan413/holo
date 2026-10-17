# Binary search

Binary search finds a target value in a sorted array by repeatedly halving the part of the array that could contain it. It only works when the data is sorted.

## How it works

Keep two indices, low and high, that mark the current search range. Compute the middle index, mid. If the element at mid equals the target, return mid. If the target is smaller, continue in the left half by setting high to mid - 1. If the target is larger, continue in the right half by setting low to mid + 1. Stop when low is greater than high, which means the target is not present.

## Complexity

Each step halves the range, so the time complexity is O(log n). Linear search takes O(n), so binary search is much faster on large sorted arrays. The extra space needed is O(1) for the iterative version.

## Common mistake

Computing mid as (low + high) / 2 can overflow in languages with fixed-size integers. Use low + (high - low) / 2 instead.
