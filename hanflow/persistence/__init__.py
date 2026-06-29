"""L5 persistence layer — three stores + workspace + resume.

All engine/worker state is externalised here, which is what makes them
stateless and horizontally scalable. See detailed design §9.
"""
