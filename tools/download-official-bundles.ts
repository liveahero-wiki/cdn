// Node modules.
import { dirname } from 'path';
import _ from 'lodash';
import fs from 'fs-extra';
import fetch, { RequestInit } from 'node-fetch';
import appRoot from 'app-root-path';

const API_URL = 'https://gateway.live-a-hero.jp';
const STATIC_URL = 'https://d1itvxfdul6wxg.cloudfront.net';
const BASE_FETCH_OPTIONS = {
  headers: { 'User-Agent': `LiveAHeroAPI` },
};
const BUNDLES_DIR = `${appRoot}/bundles`;
const ASSETLIST_PATH = `${appRoot}/version/assetList.Android`;

const getVersion = async (options: RequestInit) => {
  const forceVersion = process.env.FORCE_VERSION;
  console.log(`ForceVersion: ${forceVersion}`);
  if (forceVersion && forceVersion != "") {
    return { appVersion: forceVersion }
  }

  const res = await fetch(`${API_URL}/api/status/version`, options);

  if (res.ok) {
    // {"result":true,"message":"","client":"1.0.3","master":33}
    const { client, master } = await res.json();

    return {
      appVersion: client,
      masterVersion: master,
    };
  } else {
    return {};
  }
};

const getDiffAssetList = async (options: RequestInit, appVersion: string) => {
  const url = `${STATIC_URL}/${appVersion}/assetList.Android`;
  const res = await fetch(url, options);

  const listAssets = (raw: string) => raw.split('\n').filter(Boolean).map((line) => {
    const [filePath, hashCode, fileSize] = line.split(',');
    return { filePath, hashCode, fileSize: Number(fileSize) };
  });

  if (res.ok) {
    // Assetbundle/Android/dicing_kouki_h01_skin1_assets_fg_kouki_h01_skin1_1d7f5fc9c6c0d87841618de6de11deda.bundle,0a0e9494875f3c484d4ff6e667de5f6e,1005631
    // Assetbundle/Android/crowne_assets_icon_crowne_h01_skin1_25b59b7548f66a0b24870ae6d634e723.bundle,784fd433e85744005959e4365c8140ba,13132
    const data = await res.text();
    await fs.writeFile(`${ASSETLIST_PATH}.cache`, data);

    const currentAssetList = listAssets(data);
    let previousAssetList = listAssets(await fs.readFile(ASSETLIST_PATH, 'utf-8'));
    
    const downloadAll = process.env.DOWNLOAD_ALL;
    console.log(`DownloadAll: ${downloadAll}`);
    if (downloadAll && downloadAll != "0") {
      previousAssetList.length = 0;
    }
    
    const differentAssetList = _.differenceBy(currentAssetList, previousAssetList, 'filePath');

    console.log(differentAssetList);

    return differentAssetList;
  }

  return [];
};

const downloadAsset = async (filePath: string, appVersion: string) => {
  const url = `${STATIC_URL}/${appVersion}/${filePath}`;
  const res = await fetch(url);

  await new Promise((resolve, reject) => {
    const fileStream = fs.createWriteStream(`${BUNDLES_DIR}/${filePath}`);
    res.body.pipe(fileStream);
    res.body.on('error', reject);
    fileStream.on('finish', resolve);
  });
};

const main = async () => {
  // Step 1: get app version info.
  const { appVersion } = await getVersion(BASE_FETCH_OPTIONS);
  const options = {
    ...BASE_FETCH_OPTIONS,
    headers: {
      ...BASE_FETCH_OPTIONS.headers,
      'User-Agent': `LiveAHeroAPI/${appVersion}`,
    },
  };

  // Store the version info.
  if (!appVersion) {
    console.warn('Cannot get version from server');
    process.exit(0);
  }

  console.log(`Version: ${appVersion}`);

  // Step 2: get asset list and download the assets.
  const assetList = await getDiffAssetList(options, appVersion);

  let failed: string[] = [];

  let i = 0;
  for await (const asset of assetList) {
    const index = i++;
    await fs.mkdirp(`${BUNDLES_DIR}/${dirname(asset.filePath)}`);
    try {
      await downloadAsset(asset.filePath, appVersion);
      console.log(`[${index} / ${assetList.length}] ${asset.filePath}`);
    } catch (e) {
      failed.push(asset.filePath)
      let filePath = `${BUNDLES_DIR}/${asset.filePath}`;
      console.warn(`[${index} / ${assetList.length}] ${asset.filePath}`);
      fs.exists(filePath, function(exists) {
        if (exists) {
          console.log('File exists. Deleting now ...');
          fs.unlinkSync(filePath);
        } else {
          console.log('File not found, so not deleting.');
        }
      });
    }
  }

  // Step 3: Retire old assetList.Android.
  await fs.remove(ASSETLIST_PATH);
  await fs.move(`${ASSETLIST_PATH}.cache`, ASSETLIST_PATH);

  console.log('Download finished');
  console.log("Failed:", failed);
};

main();
