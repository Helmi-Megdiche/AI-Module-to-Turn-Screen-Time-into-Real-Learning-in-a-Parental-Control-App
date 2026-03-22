/**
 * HTTP entrypoint for the Express API (parental-control backend).
 * Loads environment from `.env`, mounts routes from `src/app.js`, listens on PORT (default 3000).
 */
require('dotenv').config();

const app = require('./src/app');

const PORT = process.env.PORT || 3000;

app.listen(PORT, () => {
  console.log(`Server running at http://localhost:${PORT}`);
});
