import axios from "axios";

const client = axios.create({
  // TODO(Person 4): replace local URL with deployed API gateway / reverse proxy URL
  baseURL: import.meta.env.VITE_API_BASE_URL || "http://localhost:8000",
  timeout: 10000,
});

export default client;