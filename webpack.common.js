const webpack = require('webpack')
const path = require('path')
const CopyWebpackPlugin = require('copy-webpack-plugin')
const MiniCssExtractPlugin = require('mini-css-extract-plugin')

module.exports = {
  entry: {
    base: {
      import: [
        './wine_cellar/assets/css/menu.css',
        './wine_cellar/assets/css/detail.css',
        './wine_cellar/assets/css/utility.css',
        './wine_cellar/assets/css/card.css',
        './wine_cellar/assets/css/forms.css',
        './wine_cellar/assets/css/styles.css',
        './wine_cellar/assets/css/page-layout.css',
        './wine_cellar/assets/css/homepage.css',
        './wine_cellar/assets/css/scan.css',
        './node_modules/tom-select/dist/css/tom-select.css',
        './node_modules/@fortawesome/fontawesome-free/css/fontawesome.css',
        './node_modules/@fortawesome/fontawesome-free/css/solid.css',
      ]
    },
    tom_select: {
      import: [
        './wine_cellar/assets/js/init_tom_select.ts'
      ],
    },
    barcode_scanner: {
      import: [
        './wine_cellar/react/react_bar_code.jsx'
      ],
    }
  },
  output: {
    path: path.resolve('./wine_cellar/static/'),
    publicPath: '/static/'
  },
  externals: {
    django: 'django'
  },
  module: {
    rules: [
      {
        test: /\.jsx?$/,
        exclude: /node_modules\/.*/, // exclude most dependencies
        loader: 'babel-loader',
        options: {
          presets: ['@babel/preset-env', '@babel/preset-react'].map(require.resolve),
          plugins: ['@babel/plugin-transform-runtime', '@babel/plugin-transform-modules-commonjs']
        }
      },
      {
        test: /\.tsx?$/,
        use: 'ts-loader',
        exclude: /node_modules/,
      },
      {
        test: /\.s?css$/,
        use: [
          {
            loader: MiniCssExtractPlugin.loader
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
                }
              }
            }
          },
          {
            loader: 'postcss-loader',
            options: {
              postcssOptions: {
                plugins: [
                  require('autoprefixer')
                ]
              }
            }
          },
        ]
      },
      {
        test: /fonts\/.*\.(svg|woff2?|ttf|eot)(\?.*)?$/,
        type: 'asset/resource',
        generator: {
          filename: 'fonts/[name][ext]'
        }
      },
      {
        test: /\.svg$|\.png$/,
        type: 'asset/resource',
        generator: {
          filename: 'images/[name][ext]'
        }
      }
    ]
  },
  resolve: {
    fallback: { path: require.resolve('path-browserify') },
    extensions: ['*', '.js', '.jsx', '.scss', '.css', '.ts', '.tsx'],
    alias: {
    },
    // when using `npm link`, dependencies are resolved against the linked
    // folder by default. This may result in dependencies being included twice.
    // Setting `resolve.root` forces webpack to resolve all dependencies
    // against the local directory.
    modules: [path.resolve('./node_modules')]
  },
  plugins: [
    new MiniCssExtractPlugin({
      filename: '[name].css',
      chunkFilename: '[name].css'
    }),
    new CopyWebpackPlugin({
      patterns: [{
        from: './wine_cellar/assets/images/**/*',
        to: 'images/[name][ext]'
      }]
    })
  ]
}
