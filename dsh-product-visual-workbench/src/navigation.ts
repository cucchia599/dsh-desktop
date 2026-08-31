export function dshHomeUrl(currentUrl: string): string {
  const url = new URL(currentUrl);
  const marker = "/product-visual-workbench";
  const routeIndex = url.pathname.indexOf(marker);
  const rootPath = routeIndex >= 0 ? url.pathname.slice(0, routeIndex) || "/" : "/";
  url.pathname = rootPath.endsWith("/") ? rootPath : `${rootPath}/`;
  url.search = "";
  url.hash = "";
  return url.toString();
}
