mkdir ~/ffmpeg_sources
cd ~/ffmpeg_sources
mkdir bin

# Used this specific release so that it doesn't complain about libc being outdated on the base image
git clone --depth 1 --branch v2.1.0 https://github.com/cisco/openh264.git

cd openh264

sed -i -e "s|PREFIX=/usr/local|" Makefile
make install

cd ~/ffmpeg_sources && \
git -C SVT-AV1 pull 2> /dev/null || git clone https://gitlab.com/AOMediaCodec/SVT-AV1.git && \
mkdir -p SVT-AV1/build && \
cd SVT-AV1/build && \
PATH="$HOME/bin:$PATH" cmake -G "Unix Makefiles" -DCMAKE_INSTALL_PREFIX="/usr/local" -DCMAKE_BUILD_TYPE=Release -DBUILD_DEC=OFF -DBUILD_SHARED_LIBS=ON .. && \
PATH="$HOME/bin:$PATH" make -j$(nproc) && \
make install