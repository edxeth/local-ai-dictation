import type { ElectrobunConfig } from "electrobun";

export default {
  app: {
    name: "parakeet-desktop",
    identifier: "parakeet.desktop.local",
    version: "0.0.1",
  },
  runtime: {
    exitOnLastWindowClosed: false,
  },
  build: {
    bun: {
      entrypoint: "src/bun/index.ts",
    },
    views: {
      mainview: {
        entrypoint: "src/mainview/index.ts",
      },
    },
    copy: {
      "src/mainview/index.html": "views/mainview/index.html",
      "src/mainview/index.css": "views/mainview/index.css",
      "src/mainview/assets/parakeet-icon.svg": "views/mainview/assets/parakeet-icon.svg",
      "src/mainview/assets/parakeet-icon.png": "views/mainview/assets/parakeet-icon.png",
    },
    mac: {
      bundleCEF: false,
    },
    linux: {
      bundleCEF: false,
      icon: "src/mainview/assets/parakeet-icon.png",
    },
    win: {
      bundleCEF: false,
      icon: "src/mainview/assets/parakeet-icon.ico",
    },
  },
} satisfies ElectrobunConfig;
