// Idempotent initialization of this project replica set only. Never reconfigure an existing set.
try {
  const existing = rs.conf();
  if (existing._id !== 'quantora-rs') throw new Error('Unexpected replica-set identity');
} catch (error) {
  if (error.code !== 94 && error.codeName !== 'NotYetInitialized') throw error;
  rs.initiate({ _id: 'quantora-rs', members: [{ _id: 0, host: 'mongodb:27017' }] });
}
let primary = false;
for (let i = 0; i < 60; i++) {
  if (db.adminCommand({ hello: 1 }).isWritablePrimary) { primary = true; break; }
  sleep(1000);
}
if (!primary) throw new Error('Replica set did not elect a primary');
