const path = require('path')
const CopyWebpackPlugin = require('copy-webpack-plugin')
const MiniCssExtractPlugin = require('mini-css-extract-plugin')
const BundleTracker = require('webpack-bundle-tracker')

module.exports = {
  entry: {
    base: {
      import: [
        './node_modules/tom-select/dist/css/tom-select.css',
        './node_modules/@fortawesome/fontawesome-free/css/fontawesome.css',
        './node_modules/@fortawesome/fontawesome-free/css/solid.css',
        './node_modules/@fortawesome/fontawesome-free/css/regular.css',
        './node_modules/purecss/build/pure.css',
        './node_modules/purecss/build/grids-responsive.css',
        './wine_cellar/assets/css/menu.css',
        './wine_cellar/assets/css/detail.css',
        './wine_cellar/assets/css/utility.css',
        './wine_cellar/assets/css/card.css',
        './wine_cellar/assets/css/timeline.css',
        './wine_cellar/assets/css/forms.css',
        './wine_cellar/assets/css/styles.css',
        './wine_cellar/assets/css/page-layout.css',
        './wine_cellar/assets/css/homepage.css',
        './wine_cellar/assets/css/button.css',
        './wine_cellar/assets/css/spinner.css',
      ],
    },
    tom_select: {
      import: ['./wine_cellar/assets/js/init_tom_select.ts'],
    },
    stock_add: {
      import: [
        './wine_cellar/assets/css/stock_picker.css',
        './wine_cellar/assets/js/stock_add.ts',
      ],
    },
    barcode_scanner: {
      import: ['./wine_cellar/react/react_bar_code.tsx'],
    },
    maps: {
      import: [
        'leaflet/dist/leaflet.css',
        'maplibre-gl/dist/maplibre-gl.css',
        'leaflet.markercluster/dist/MarkerCluster.css',
        './wine_cellar/assets/css/map.css',
        './wine_cellar/react/maps/react_maps.tsx',
      ],
    },
    react_choose_point: {
      import: [
        'leaflet/dist/leaflet.css',
        'maplibre-gl/dist/maplibre-gl.css',
        './wine_cellar/assets/css/map.css',
        './wine_cellar/react/maps/react_choose_point.tsx',
      ],
    },
    wine_carousel: {
      import: ['./wine_cellar/assets/js/wine_carousel.ts'],
    },
    vintage_tabs: {
      import: ['./wine_cellar/assets/js/vintage_tabs.ts'],
    },
    image_preview: {
      import: ['./wine_cellar/assets/js/image_preview.ts'],
    },
    stock_drag: {
      import: ['./wine_cellar/assets/js/stock_drag.ts'],
    },
    wine_upload_ai: {
      import: ['./wine_cellar/assets/js/wine_upload_ai.ts'],
    },
  },
  output: {
    path: path.resolve('./wine_cellar/static/'),
    publicPath: 'auto',
  },
  externals: {
    django: 'django',
  },
  optimization: {
    splitChunks: {
      cacheGroups: {
        maplibre: {
          test: /[\\/]node_modules[\\/](maplibre-gl|@maplibre)[\\/]/,
          name: 'vendor-maplibre',
          chunks: 'all',
          enforce: true,
        },
        react: {
          test: /[\\/]node_modules[\\/](react|react-dom|scheduler)[\\/]/,
          name: 'vendor-react',
          chunks: 'all',
          enforce: true,
        },
      },
    },
  },
  module: {
    rules: [
      {
        test: /\.tsx?$/,
        use: 'ts-loader',
        exclude: /node_modules/,
      },
      {
        test: /\.css$/,
        use: [
          {
            loader: MiniCssExtractPlugin.loader,
          },
          {
            loader: 'css-loader',
            options: {
              url: {
                filter: (url, resourcePath) => {
                  // only handle `/` urls, leave rest in code (pythong images to be left)
                  if (!url.startsWith('/')) {
                    return true
                  } else {
                    return false
                  }
                },
              },
            },
          },
          {
            loader: 'postcss-loader',
            options: {
              postcssOptions: {
                plugins: [require('autoprefixer')],
              },
            },
          },
        ],
      },
      {
        test: /fonts\/.*\.(svg|woff2?|ttf|eot)(\?.*)?$/,
        type: 'asset/resource',
        generator: {
          filename: 'fonts/[name][ext]',
        },
      },
      {
        test: /\.svg$|\.png$/,
        type: 'asset/resource',
        generator: {
          filename: 'images/[name][ext]',
        },
      },
    ],
  },
  resolve: {
    extensions: ['*', '.js', '.jsx', '.css', '.ts', '.tsx'],
    alias: {},
    // when using `npm link`, dependencies are resolved against the linked
    // folder by default. This may result in dependencies being included twice.
    // Setting `resolve.root` forces webpack to resolve all dependencies
    // against the local directory. Keep the default 'node_modules' lookup
    // too, so nested (non-hoisted) transitive deps still resolve.
    modules: ['node_modules', path.resolve('./node_modules')],
  },
  plugins: [
    new MiniCssExtractPlugin({
      filename: '[name].css',
      chunkFilename: '[name].css',
    }),
    new CopyWebpackPlugin({
      patterns: [
        {
          from: './wine_cellar/assets/images/**/*',
          to: 'images/[name][ext]',
        },
        {
          from: './wine_cellar/assets/js/index.js.map',
          to: '[name][ext]',
        },
        {
          from: './node_modules/zxing-wasm/dist/reader/zxing_reader.wasm',
          to: '[name][ext]',
        },
      ],
    }),
    new BundleTracker({
      path: path.resolve('.'),
      filename: 'webpack-stats.json',
    }),
  ],
}
