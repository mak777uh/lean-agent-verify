theorem proof : ¬ statementProp := fun h => Nat.lt_irrefl 0 (h 0)
