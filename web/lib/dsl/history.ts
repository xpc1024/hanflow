export class History<T> {
  private undoStack: T[] = [];
  private redoStack: T[] = [];

  constructor(private max: number = 50) {}

  push(s: T): void {
    this.undoStack.push(s);
    this.redoStack = [];
    if (this.undoStack.length > this.max) this.undoStack.shift();
  }

  undoPop(): T | null {
    const s = this.undoStack.pop();
    if (s !== undefined) {
      this.redoStack.push(s);
      return s;
    }
    return null;
  }

  redoPop(): T | null {
    const s = this.redoStack.pop();
    if (s !== undefined) {
      this.undoStack.push(s);
      return s;
    }
    return null;
  }

  canUndo(): boolean {
    return this.undoStack.length > 0;
  }

  canRedo(): boolean {
    return this.redoStack.length > 0;
  }

  clear(): void {
    this.undoStack = [];
    this.redoStack = [];
  }
}
