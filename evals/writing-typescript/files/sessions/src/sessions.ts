export interface Session {
  userId: string;
  /** Epoch milliseconds. */
  startedAt: number;
  /** Epoch milliseconds, or null while the session is still open. */
  endedAt: number | null;
}

export class SessionStore {
  private byUser = new Map<string, Session[]>();

  add(session: Session): void {
    const list = this.byUser.get(session.userId) ?? [];
    list.push(session);
    this.byUser.set(session.userId, list);
  }

  sessionsFor(userId: string): Session[] {
    return this.byUser.get(userId) ?? [];
  }

  totalMinutes(userId: string, now: number = Date.now()): number {
    let ms = 0;
    for (const s of this.sessionsFor(userId)) {
      ms += (s.endedAt ?? now) - s.startedAt;
    }
    return Math.round(ms / 60000);
  }
}
