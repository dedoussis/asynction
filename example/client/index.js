// Setup basic express server
const express = require("express");
const app = express();
const path = require("path");
const server = require("http").createServer(app);
const port = process.env.PORT || 3000;

server.listen(port, () => {
  console.log("Server listening at port %d", port);
});

// Routing
app.use(express.static(path.join(__dirname, "public")));
