echo "##################################################"
echo "######### Running case: Hello World ##############"
echo "##################################################"

# Export install directory
export CASE_INSTALL_DIR=$(pwd)/install

echo "##################################################"
echo "### Step 1: Build and install t8code"
echo "##################################################"
cd libs/t8code-build

echo "--------------------------------------------------"
echo "(1.a) Run cmake"
echo "--------------------------------------------------"
cmake ../t8code-src/ -GNinja -DCMAKE_INSTALL_PREFIX=$CASE_INSTALL_DIR

echo "--------------------------------------------------"
echo "(1.b) Run ninja"
echo "--------------------------------------------------"
ninja -j 32

echo "--------------------------------------------------"
echo "(1.c) Run ninja install"
echo "--------------------------------------------------"
ninja install

cd -

echo "##################################################"
echo "### Step 2: Build project hello_world"
echo "##################################################"

# Enter folder
mkdir -p build && cd build

echo "--------------------------------------------------"
echo "(1.a) Run cmake"
echo "--------------------------------------------------"
cmake .. -GNinja -DCMAKE_PREFIX_PATH=$CASE_INSTALL_DIR

echo "--------------------------------------------------"
echo "(1.b) Run ninja"
echo "--------------------------------------------------"
ninja -j 32

echo "##################################################"
echo "### Step 3: Run executable hello_world"
echo "##################################################"

# Run the case and pipe into log
echo "mpirun -np 4 ./hello_world > log"
mpirun -np 4 ./hello_world > log

echo "##################################################"
echo "### Step 4: (Pseudo-)Post-Processing"
echo "##################################################"

echo "The program produced the following output:"
echo -e "\033[33m$(cat log)\033[0m"

echo "##################################################"
echo "############# Leaving without errors #############"
echo "##################################################"

# Exit without error
exit 0
