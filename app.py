import streamlit as st
import pandas as pd
import datetime

# --- Page Configuration ---
st.set_page_config(
    page_title="Import File Generator",
    page_icon="📦",
    layout="wide"
)

# --- Password Protection ---
def check_password():
    """Returns `True` if the user entered the correct password."""
    def password_entered():
        """Checks whether a password entered by the user is correct."""
        if st.session_state["password"] == st.secrets["password"]:
            st.session_state["password_correct"] = True
            del st.session_state["password"]  # Don't store the password.
        else:
            st.session_state["password_correct"] = False

    # Return `True` if the password is correct.
    if st.session_state.get("password_correct", False):
        return True

    # Show input for password.
    st.text_input(
        "Password", type="password", on_change=password_entered, key="password"
    )
    if "password_correct" in st.session_state and not st.session_state["password_correct"]:
        st.error("😕 Password incorrect")
    return False


if not check_password():
    st.stop()  # Do not continue if the password is wrong.


# --- App Title and Description ---
st.title("📦 Antique Candle Works Import File Generator")
st.markdown("""
Upload your main CSV file to automatically generate the necessary import files for **NetSuite** and **Shopify**.
Ensure your uploaded CSV contains the following columns: `SKU`, `Fragrance - Vessel Description`, `Retail Price`, `End Weight (lbs)`, `Quantity`, `Burn Time`, `Height`, and `Width`.
""")

# --- Instructions Expander ---
with st.expander("Show/Hide Instructions"):
    st.markdown("""
    ### Antique Item Creation Steps

    ---

    #### **Requirements**
    - The antique spreadsheet from Dropbox, usually shared by Emily.
    - A local copy of the spreadsheet saved in CSV format.

    ---

    #### **File Preparation & Generation**
    1.  **Download** the antiques file from Dropbox.
    2.  Emily usually has some additional calculation data to the right and below the main item data. This **must be deleted** before you save the sheet as a `.csv` file.
    3.  **Save** the cleaned sheet as a `.csv` file in a memorable location on your computer.
    4.  Use the **"Choose your source CSV file"** button below to upload the `.csv` file you just saved.
    5.  The app will generate three new files for you to download:
        - `netsuite_import_MM_DD_YY.csv`
        - `shopify_import_MM_DD_YY.csv`
        - `inventory_adjustment_MM_DD_YY.csv`

    ---

    #### **1. NetSuite Item Import**
    > **IMPORTANT**: This must be completed successfully *before* starting the Shopify import.
    1.  In NetSuite, navigate to **Setup > Import/Export > Saved CSV Imports**.
    2.  Find and open import **ID 153** (Antiques Import - 06_17_2022).
    3.  Under "Import File," click **Select** and choose your `netsuite_import_MM_DD_YY.csv` file. Click **Next**.
    4.  Set the Import Type to **ADD** and click **Next**.
    5.  On the mapping page, drag **`itemid`** from the left panel to the **Item Name/Number** field on the right. Click **Next**.
    6.  On the final page, click **Run** to start the import.
    7.  After the job completes, verify that the number of records imported matches the number of items from your file.

    ---

    #### **2. Shopify Product Import**
    1.  In Shopify, go to **Products** and click the **Import** button in the top right.
    2.  Add your `shopify_import_MM_DD_YY.csv` file.
    3.  **Uncheck** the box for "Publish new products to all sales channels."
    4.  **Check** the box for "Overwrite products with matching handles."
    5.  Click **Upload and preview**.
    6.  Review the preview to ensure the data looks correct, then click **Import Products**.

    ---

    #### **3. NetSuite Inventory Adjustment**
    1.  In NetSuite, navigate to **Setup > Import/Export > Saved CSV Imports**.
    2.  Find and open the **Invadjust 04_18 antiques import**.
    3.  Choose your `inventory_adjustment_MM_DD_YY.csv` file and click **Next**.
    4.  Under Import Options, select **ADD** and click **Next**.
    5.  On the mapping page, click the **date** field to update it to the current date, then click **Next**.
    6.  Click **Run** to start the import. Monitor the import job status to ensure it completes.

    ---

    #### **4. Celigo Troubleshooting**
    > This is only needed if items were imported out of sequence or if inventory quantities appear incorrect. Celigo typically syncs automatically every 15-30 minutes.
    1.  In Celigo, navigate to the **Shopify - NetSuite IO** integration tile.
    2.  Go to the **Inventory** flows section.
    3.  Run the **Shopify Product ID to NetSuite Item Mass Update** flow. You may need to set the start date back to ensure all new items are included.
    4.  Once that completes, run the **NetSuite Inventory to Shopify Inventory Add/Update** flow to sync the adjusted quantities to Shopify.
    """)

# --- File Uploader ---
uploaded_file = st.file_uploader("Choose your source CSV file", type="csv")

# --- Main Processing Logic ---
if uploaded_file is not None:
    try:
        antique_import = pd.read_csv(uploaded_file)

        # ####################################################################
        # ## Data Cleaning and Pre-processing ##
        # ####################################################################
        
        # Strip leading/trailing whitespace from all column headers
        antique_import.columns = antique_import.columns.str.strip()

        # List of columns that should be numeric
        numeric_cols_to_check = [
            'Retail Price', 'End Weight (lbs)', 'Quantity', 'Burn Time', 
            'End Weight', 'Height', 'Width'
        ]
        
        # Filter for only the numeric columns that actually exist in the dataframe
        numeric_cols = [col for col in numeric_cols_to_check if col in antique_import.columns]
        
        # Define required columns
        required_cols = ['SKU', 'Fragrance - Vessel Description', 'Retail Price', 'End Weight (lbs)', 'Quantity']
        missing_cols = [col for col in required_cols if col not in antique_import.columns]

        if missing_cols:
            st.error(f"**Error:** Your file is missing the following required columns: `{', '.join(missing_cols)}`")
            st.stop() # Stop the app if columns are missing

        # For each numeric column, convert it to a number and fill any empty/NaN values with 0
        for col in numeric_cols:
            antique_import[col] = pd.to_numeric(antique_import[col], errors='coerce').fillna(0)
        
        # Add 'End Weight' if it doesn't exist, based on 'End Weight (lbs)'
        if 'End Weight' not in antique_import.columns and 'End Weight (lbs)' in antique_import.columns:
            antique_import['End Weight'] = antique_import['End Weight (lbs)'] * 16 # Convert lbs to oz

        # ####################################################################
        
        st.success("File uploaded successfully! Here's a preview of the cleaned data:")
        st.dataframe(antique_import.head())

        # --- Initialize DataFrames ---
        netsuite_import = pd.DataFrame(columns=['externalid', 'itemid', 'Display Name', 'unitstype', 'subsidiary', 'includechildren', 'location', 'track landed cost', 'costingmethod', 'costcategory', 'atpmethod', 'autopreferredstocklevel', 'isspecialorderitem', 'usebins', 'cogsaccount', 'incomeaccount', 'assetaccount', 'taxSchedule', 'isinactive', 'Price', 'Weight'])
        shopify_import = pd.DataFrame(columns=['Handle', 'Title', 'Body (HTML)', 'Vendor', 'Tags', 'Published', 'Option1 Name', 'Option1 Value', 'Option2 Name', 'Option2 Value', 'Option3 Name', 'Option3 Value', 'Variant SKU', 'Variant Grams', 'Variant Inventory Tracker', 'Variant Inventory Qty', 'Variant Inventory Policy', 'Variant Fulfillment Service', 'Variant Price', 'Variant Compare At Price', 'Variant Requires Shipping', 'Variant Taxable', 'Variant Barcode', 'Image Src', 'Image Position', 'Image Alt Text', 'Gift Card', 'SEO Title', 'SEO Description', 'Google Shopping / Google Product Category', 'Google Shopping / Gender', 'Google Shopping / Age Group', 'Google Shopping / MPN', 'Google Shopping / AdWords Grouping', 'Google Shopping / AdWords Labels', 'Google Shopping / Condition', 'Google Shopping / Custom Product', 'Google Shopping / Custom Label 0', 'Google Shopping / Custom Label 1', 'Google Shopping / Custom Label 2', 'Google Shopping / Custom Label 3', 'Google Shopping / Custom Label 4', 'Variant Image', 'Variant Weight Unit', 'Variant Tax Code', 'Cost per item', 'Status', 'Standard Product Type', 'Custom Product Type'])
        netsuite_inventory_adjustment = pd.DataFrame(columns=['External ID', 'Full name', 'Account', 'Class', 'Department', 'memo', 'line qty adj', 'Line adj loc', 'Line memo', 'itemId'])

        # --- Data Processing Loop ---
        for index, row in antique_import.iterrows():
            # Get the original description from the uploaded file
            original_description = str(row['Fragrance - Vessel Description'])

            # Create a standardized name for NetSuite by replacing '|' with ' - '
            netsuite_display_name = ' - '.join([part.strip() for part in original_description.split('|')])

            # Create NetSuite Import row
            netsuite_import.at[index, 'externalid'] = row['SKU']
            netsuite_import.at[index, 'itemid'] = row['SKU']
            netsuite_import.at[index, 'Display Name'] = netsuite_display_name
            netsuite_import.at[index, 'unitstype'] = "Quantity"
            netsuite_import.at[index, 'location'] = 'ACC 1611'
            netsuite_import.at[index, 'track landed cost'] = 'FALSE'
            netsuite_import.at[index, 'costingmethod'] = 'AVERAGE'
            netsuite_import.at[index, 'costcategory'] = 'Default'
            netsuite_import.at[index, 'atpmethod'] = 'Discrete ATP'
            netsuite_import.at[index, 'autopreferredstocklevel'] = 'TRUE'
            netsuite_import.at[index, 'isspecialorderitem'] = 'FALSE'
            netsuite_import.at[index, 'usebins'] = 'FALSE'
            netsuite_import.at[index, 'cogsaccount'] = 318
            netsuite_import.at[index, 'incomeaccount'] = 429
            netsuite_import.at[index, 'assetaccount'] = 227
            netsuite_import.at[index, 'taxSchedule'] = 'Non-taxable'
            netsuite_import.at[index, 'isinactive'] = 'FALSE'
            netsuite_import.at[index, 'Price'] = row['Retail Price']
            netsuite_import.at[index, 'Weight'] = row['End Weight (lbs)']

            # Create NetSuite Inventory Adjustment row
            sku_str = str(row['SKU'])
            netsuite_inventory_adjustment.at[index, 'External ID'] = 'Antique Restock ' + sku_str[-6:]
            netsuite_inventory_adjustment.at[index, 'Full name'] = f"{row['SKU']} {netsuite_display_name}"
            netsuite_inventory_adjustment.at[index, 'Account'] = 325
            netsuite_inventory_adjustment.at[index, 'Class'] = 'Operations : Production'
            netsuite_inventory_adjustment.at[index, 'Department'] = 'Retail'
            netsuite_inventory_adjustment.at[index, 'memo'] = 'Antique Restock ' + sku_str[-6:]
            netsuite_inventory_adjustment.at[index, 'line qty adj'] = row['Quantity']
            netsuite_inventory_adjustment.at[index, 'Line adj loc'] = 'ACC 1611'
            netsuite_inventory_adjustment.at[index, 'Line memo'] = 'Antique Restock ' + sku_str[-6:]
            netsuite_inventory_adjustment.at[index, 'itemId'] = row['SKU']

            # Create Shopify Import row
            shopify_import.at[index, 'Handle'] = sku_str.replace(' ', '')
            # Use the original, unmodified description for the Shopify Title
            shopify_import.at[index, 'Title'] = original_description
            shopify_import.at[index, 'Body (HTML)'] = f"""
                <p data-mce-fragment="1">Approximate Burn Time: {row['Burn Time']} hours</p>
                <p data-mce-fragment="1">Weight: {row['End Weight']} oz</p>
                <p data-mce-fragment="1">Dimensions: {row.get('Height', 'N/A')}" Height x {row.get('Width', 'N/A')}" Width</p>
            """
            
            # For tag generation, temporarily replace '|' with '-' to correctly parse the fragrance
            parseable_name_for_tags = original_description.replace('|', '-')
            fragrance = parseable_name_for_tags.split('-')[0].strip()
            smells_like = fragrance.replace(' ', '-').lower()
            shopify_import.at[index, 'Tags'] = f"_tab2_antique-restock-101,antique{sku_str[-6:]},_tab1_{smells_like}-smells-like, {fragrance}"
            
            shopify_import.at[index, 'Published'] = 'FALSE'
            shopify_import.at[index, 'Variant SKU'] = row['SKU']
            shopify_import.at[index, 'Variant Grams'] = round(row['End Weight (lbs)'] * 453.592)
            shopify_import.at[index, 'Variant Inventory Tracker'] = 'shopify'
            shopify_import.at[index, 'Variant Inventory Policy'] = 'deny'
            shopify_import.at[index, 'Variant Fulfillment Service'] = 'manual'
            shopify_import.at[index, 'Variant Price'] = row['Retail Price']
            shopify_import.at[index, 'Variant Requires Shipping'] = 'TRUE'
            shopify_import.at[index, 'Variant Taxable'] = 'TRUE'
            shopify_import.at[index, 'Gift Card'] = 'FALSE'
            shopify_import.at[index, 'Variant Weight Unit'] = 'lb'
            shopify_import.at[index, 'Status'] = 'active'

        st.info("✅ Processing complete. Your files are ready for download below.")

        today = datetime.date.today().strftime("%m_%d_%y")
        
        @st.cache_data
        def convert_df_to_csv(df):
            return df.to_csv(index=False).encode('utf-8')

        col1, col2, col3 = st.columns(3)

        with col1:
            st.header("NetSuite Import")
            st.dataframe(netsuite_import, use_container_width=True)
            st.download_button(label="📥 Download NetSuite Import", data=convert_df_to_csv(netsuite_import), file_name=f"netsuite_import_{today}.csv", mime="text/csv", use_container_width=True)

        with col2:
            st.header("Shopify Import")
            st.dataframe(shopify_import, use_container_width=True)
            st.download_button(label="📥 Download Shopify Import", data=convert_df_to_csv(shopify_import), file_name=f"shopify_import_{today}.csv", mime="text/csv", use_container_width=True)
            
        with col3:
            st.header("Inventory Adjustment")
            st.dataframe(netsuite_inventory_adjustment, use_container_width=True)
            st.download_button(label="📥 Download Inventory Adjustment", data=convert_df_to_csv(netsuite_inventory_adjustment), file_name=f"inventory_adjustment_{today}.csv", mime="text/csv", use_container_width=True)

    except Exception as e:
        st.error(f"An unexpected error occurred: {e}")