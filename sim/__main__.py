"""Allow `python -m sim` to work as an alias for `python -m sim.runner`."""
from sim.runner import main

if __name__ == "__main__":
    main()
